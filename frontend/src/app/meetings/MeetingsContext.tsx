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
import type { CreateMeetingParticipantInput } from './api';
import * as meetingsApi from './api';

interface CreateMeetingInput {
  title: string;
  description?: string;
  startTime: Date;
  endTime: Date;
  participants: CreateMeetingParticipantInput[];
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
const AI_SUMMARY_PREFETCH_LIMIT = 4;

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

  const hydrateMeetingsWithAnalysis = useCallback(async (items: Meeting[]) => {
    const candidates = [...items]
      .filter(
        (meeting) =>
          meeting.status === 'completed' &&
          meeting.sessionId &&
          meeting.analysis?.aiStatus === 'ready' &&
          !meeting.aiSummary,
      )
      .sort((left, right) => right.startTime.getTime() - left.startTime.getTime())
      .slice(0, AI_SUMMARY_PREFETCH_LIMIT);

    if (candidates.length === 0) {
      return items;
    }

    const results = await Promise.allSettled(
      candidates.map(async (meeting) => ({
        meetingId: meeting.id,
        merged: meetingsApi.mergeMeetingAnalysis(
          meeting,
          await meetingsApi.getMeetingAnalysis(meeting.id),
        ),
      })),
    );

    const mergedById = new Map<string, Meeting>();
    for (const result of results) {
      if (result.status === 'fulfilled') {
        mergedById.set(result.value.meetingId, result.value.merged);
      }
    }

    if (mergedById.size === 0) {
      return items;
    }

    return items.map((meeting) => mergedById.get(meeting.id) ?? meeting);
  }, []);

  const refreshMeetings = useCallback(async () => {
    setIsLoading(true);
    try {
      const nextMeetings = await meetingsApi.listMeetings();
      setMeetings(nextMeetings);
      setError(null);
      void hydrateMeetingsWithAnalysis(nextMeetings)
        .then((enrichedMeetings) => {
          if (enrichedMeetings !== nextMeetings) {
            setMeetings(enrichedMeetings);
          }
        })
        .catch(() => {
          // Listeleme ekranlarini bozmayalim; analysis detaylari arka planda yuklenebilir.
        });
    } catch (err: any) {
      setError(err?.message ?? 'Toplantilar yuklenemedi');
    } finally {
      setIsLoading(false);
    }
  }, [hydrateMeetingsWithAnalysis]);

  useEffect(() => {
    void refreshMeetings();
  }, [refreshMeetings]);

  const createMeeting = useCallback(async (input: CreateMeetingInput) => {
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
  }, []);

  const fetchMeetingById = useCallback(async (id: string) => {
    try {
      const meeting = await meetingsApi.getMeeting(id);
      setMeetings((current) => upsertMeeting(current, meeting));
      setError(null);
      return meeting;
    } catch (err: any) {
      setError(err?.message ?? 'Toplanti yuklenemedi');
      return null;
    }
  }, []);

  const getCachedMeetingById = useCallback(
    (id: string) => meetings.find((meeting) => meeting.id === id) ?? null,
    [meetings],
  );

  const setMeeting = useCallback((meeting: Meeting) => {
    setMeetings((current) => upsertMeeting(current, meeting));
  }, []);

  const value = useMemo<MeetingsContextValue>(
    () => ({
      meetings,
      isLoading,
      error,
      refreshMeetings,
      createMeeting,
      fetchMeetingById,
      getCachedMeetingById,
      setMeeting,
    }),
    [createMeeting, error, fetchMeetingById, getCachedMeetingById, isLoading, meetings, refreshMeetings, setMeeting],
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
