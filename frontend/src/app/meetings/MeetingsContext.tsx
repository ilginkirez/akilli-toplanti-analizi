import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import type { AgendaItem, Meeting, User } from '../types';
import * as meetingsApi from './api';

interface CreateMeetingInput {
  title: string;
  description?: string;
  startTime: Date;
  endTime: Date;
  participants: User[];
  agenda: Array<Pick<AgendaItem, 'title' | 'duration'>>;
  organizer: User;
}

interface MeetingsContextValue {
  meetings: Meeting[];
  isLoading: boolean;
  error: string | null;
  refreshMeetings: () => Promise<void>;
  createMeeting: (input: CreateMeetingInput) => Promise<Meeting>;
  fetchMeetingById: (id: string) => Promise<Meeting | null>;
  getCachedMeetingById: (id: string) => Meeting | null;
  setMeeting: (meeting: Meeting) => void;
}

const MeetingsContext = createContext<MeetingsContextValue | undefined>(undefined);

function upsertMeeting(list: Meeting[], nextMeeting: Meeting): Meeting[] {
  const existingIndex = list.findIndex((meeting) => meeting.id === nextMeeting.id);
  if (existingIndex === -1) {
    return [nextMeeting, ...list];
  }

  const next = [...list];
  next[existingIndex] = nextMeeting;
  return next;
}

export function MeetingsProvider({ children }: { children: ReactNode }) {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refreshMeetings = useCallback(async () => {
    setIsLoading(true);
    try {
      const nextMeetings = await meetingsApi.listMeetings();
      setMeetings(nextMeetings);
      setError(null);
    } catch (err: any) {
      setError(err?.message ?? 'Toplantılar yüklenemedi');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshMeetings();
  }, [refreshMeetings]);

  const value = useMemo<MeetingsContextValue>(
    () => ({
      meetings,
      isLoading,
      error,
      refreshMeetings,
      createMeeting: async (input) => {
        const nextMeeting = await meetingsApi.createMeeting({
          title: input.title.trim(),
          description: input.description?.trim() || undefined,
          scheduledStart: input.startTime.toISOString(),
          scheduledEnd: input.endTime.toISOString(),
          organizer: input.organizer,
          participants: input.participants,
          agenda: input.agenda.map((item) => ({
            title: item.title.trim(),
            duration: item.duration,
          })),
        });
        setMeetings((current) => upsertMeeting(current, nextMeeting));
        setError(null);
        return nextMeeting;
      },
      fetchMeetingById: async (id) => {
        try {
          const meeting = await meetingsApi.getMeeting(id);
          setMeetings((current) => upsertMeeting(current, meeting));
          setError(null);
          return meeting;
        } catch (err: any) {
          setError(err?.message ?? 'Toplantı yüklenemedi');
          return null;
        }
      },
      getCachedMeetingById: (id) => meetings.find((meeting) => meeting.id === id) ?? null,
      setMeeting: (meeting) => {
        setMeetings((current) => upsertMeeting(current, meeting));
      },
    }),
    [error, isLoading, meetings, refreshMeetings],
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
