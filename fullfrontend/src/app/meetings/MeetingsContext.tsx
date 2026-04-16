import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import { mockMeetings, mockUsers } from '../data/mockData';
import type { AgendaItem, Meeting, User } from '../types';

const CREATED_MEETINGS_STORAGE_KEY = 'meetingai.createdMeetings';

interface CreateMeetingInput {
  title: string;
  description?: string;
  startTime: Date;
  endTime: Date;
  participantIds: string[];
  agenda: Array<Pick<AgendaItem, 'title' | 'duration'>>;
  organizer: User;
}

interface StoredCreatedMeeting {
  id: string;
  title: string;
  description?: string;
  startTime: string;
  endTime: string;
  organizerId: string;
  participantIds: string[];
  agenda: AgendaItem[];
}

interface MeetingsContextValue {
  meetings: Meeting[];
  createMeeting: (input: CreateMeetingInput) => Meeting;
  getMeetingById: (id: string) => Meeting | null;
}

const MeetingsContext = createContext<MeetingsContextValue | undefined>(undefined);

function getUserById(userId: string) {
  return mockUsers.find((user) => user.id === userId) ?? mockUsers[0];
}

function resolveMeetingStatus(startTime: Date, endTime: Date): Meeting['status'] {
  const now = Date.now();

  if (endTime.getTime() <= now) {
    return 'completed';
  }

  if (startTime.getTime() <= now && endTime.getTime() > now) {
    return 'in-progress';
  }

  return 'upcoming';
}

function createMeetingId() {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return `m-${crypto.randomUUID().slice(0, 8)}`;
  }

  return `m-${Date.now().toString(36)}`;
}

function deserializeCreatedMeeting(record: StoredCreatedMeeting): Meeting {
  const organizer = getUserById(record.organizerId);
  const participantIds = Array.from(
    new Set([organizer.id, ...record.participantIds.filter(Boolean)]),
  );
  const startTime = new Date(record.startTime);
  const endTime = new Date(record.endTime);

  return {
    id: record.id,
    title: record.title,
    description: record.description,
    startTime,
    endTime,
    status: resolveMeetingStatus(startTime, endTime),
    organizer,
    participants: participantIds.map((participantId) => ({
      user: getUserById(participantId),
      status: participantId === organizer.id ? 'accepted' : 'pending',
    })),
    agenda: record.agenda,
  };
}

function serializeCreatedMeeting(meeting: Meeting): StoredCreatedMeeting {
  return {
    id: meeting.id,
    title: meeting.title,
    description: meeting.description,
    startTime: meeting.startTime.toISOString(),
    endTime: meeting.endTime.toISOString(),
    organizerId: meeting.organizer.id,
    participantIds: meeting.participants.map((participant) => participant.user.id),
    agenda: meeting.agenda,
  };
}

function loadCreatedMeetings() {
  if (typeof window === 'undefined') {
    return [] as Meeting[];
  }

  try {
    const raw = window.localStorage.getItem(CREATED_MEETINGS_STORAGE_KEY);
    if (!raw) {
      return [] as Meeting[];
    }

    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return [] as Meeting[];
    }

    return parsed
      .filter((item): item is StoredCreatedMeeting => Boolean(item && typeof item === 'object'))
      .map(deserializeCreatedMeeting);
  } catch {
    return [] as Meeting[];
  }
}

export function MeetingsProvider({ children }: { children: ReactNode }) {
  const [createdMeetings, setCreatedMeetings] = useState<Meeting[]>(() => loadCreatedMeetings());

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const serialized = createdMeetings.map(serializeCreatedMeeting);
    window.localStorage.setItem(CREATED_MEETINGS_STORAGE_KEY, JSON.stringify(serialized));
  }, [createdMeetings]);

  const meetings = useMemo(
    () => [...createdMeetings, ...mockMeetings],
    [createdMeetings],
  );

  const value = useMemo<MeetingsContextValue>(
    () => ({
      meetings,
      createMeeting: (input) => {
        const participantIds = Array.from(
          new Set([input.organizer.id, ...input.participantIds.filter(Boolean)]),
        );
        const nextMeeting: Meeting = {
          id: createMeetingId(),
          title: input.title.trim(),
          description: input.description?.trim() || undefined,
          startTime: input.startTime,
          endTime: input.endTime,
          status: resolveMeetingStatus(input.startTime, input.endTime),
          organizer: input.organizer,
          participants: participantIds.map((participantId) => ({
            user: getUserById(participantId),
            status: participantId === input.organizer.id ? 'accepted' : 'pending',
          })),
          agenda: input.agenda.map((item, index) => ({
            id: `agenda-${index + 1}-${Date.now()}`,
            title: item.title.trim(),
            duration: item.duration,
            completed: false,
          })),
        };

        setCreatedMeetings((current) => [nextMeeting, ...current]);
        return nextMeeting;
      },
      getMeetingById: (id) => meetings.find((meeting) => meeting.id === id) ?? null,
    }),
    [meetings],
  );

  return <MeetingsContext.Provider value={value}>{children}</MeetingsContext.Provider>;
}

export function useMeetings() {
  const context = useContext(MeetingsContext);

  if (!context) {
    throw new Error('useMeetings must be used within MeetingsProvider');
  }

  return context;
}
