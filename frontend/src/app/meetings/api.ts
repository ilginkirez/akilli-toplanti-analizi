import { request } from '../livekit-meeting/services/api';
import type {
  AgendaItem,
  Meeting,
  MeetingAnalysisInfo,
  MeetingAnalytics,
  MeetingParticipant,
  MeetingRecording,
  MeetingTimelineSegment,
  User,
} from '../types';

type ApiOrganizer = {
  name: string;
  email: string;
  role?: User['role'];
  department?: string;
  avatar?: string | null;
};

type ApiParticipant = {
  user_id?: string | null;
  participant_type?: 'internal_user' | 'external_guest' | null;
  name: string;
  email?: string | null;
  role?: User['role'];
  department?: string | null;
  avatar?: string | null;
  status?: MeetingParticipant['status'];
  response_status?: MeetingParticipant['status'];
  joined_at?: string | null;
  left_at?: string | null;
  speaking_time?: number | null;
  camera_on_time?: number | null;
  mic_on_time?: number | null;
  participant_id?: string | null;
};

type ApiAgendaItem = {
  id?: string;
  title: string;
  duration: number;
  completed?: boolean;
};

type ApiRecording = {
  status: string;
  mode?: string | null;
  started_at?: string | null;
  stopped_at?: string | null;
  ready_at?: string | null;
  files_count?: number;
  archive_path?: string | null;
};

type ApiAnalysisInfo = {
  status: string;
  generated_at?: string | null;
  segment_count?: number;
  summary_count?: number;
};

export type ApiMeeting = {
  id: string;
  meeting_id?: string;
  title: string;
  description?: string | null;
  scheduled_start: string;
  scheduled_end: string;
  status: Meeting['status'];
  organizer: ApiOrganizer;
  participants: ApiParticipant[];
  participants_count?: number;
  agenda: ApiAgendaItem[];
  session_id?: string | null;
  recording?: ApiRecording;
  analysis?: ApiAnalysisInfo;
  created_at?: string;
  updated_at?: string;
};

export type ApiMeetingAnalysis = {
  meeting_id: string;
  session_id?: string | null;
  status: string;
  generated_at?: string | null;
  recording_status?: string;
  transcript_available: boolean;
  recording?: ApiRecording;
  timeline: Array<{
    segment_id: number | string;
    type: 'single' | 'overlap';
    overlap: boolean;
    start_sec: number;
    end_sec: number;
    duration_sec: number;
    start_at?: string | null;
    end_at?: string | null;
    participants: Array<{
      participant_id?: string;
      display_name: string;
    }>;
  }>;
  speaking_summary: Array<{
    participant_id?: string;
    display_name: string;
    segment_count: number;
    total_speaking_sec: number;
    percentage: number;
    first_spoken_sec?: number | null;
    last_spoken_sec?: number | null;
  }>;
  analytics: {
    total_participants: number;
    average_attendance: number;
    speaking_distribution: Array<{
      participant_id?: string;
      display_name: string;
      percentage: number;
      duration_sec: number;
    }>;
    engagement_score?: number | null;
    sentiment_breakdown?: {
      positive: number;
      neutral: number;
      negative: number;
    };
  };
};

export type CreateMeetingRequest = {
  title: string;
  description?: string;
  scheduledStart: string;
  scheduledEnd: string;
  organizer: User;
  participants: CreateMeetingParticipantInput[];
  agenda: Array<Pick<AgendaItem, 'title' | 'duration'>>;
};

export type CreateMeetingParticipantInput = {
  id: string;
  userId?: string;
  participantType: 'internal_user' | 'external_guest';
  name: string;
  email: string;
  avatar?: string;
  role: User['role'];
  department: string;
};

function normalizeRole(role?: string | null): User['role'] {
  return role === 'admin' || role === 'manager' ? role : 'member';
}

function mapUser(base: ApiOrganizer | ApiParticipant, fallbackId: string): User {
  const participant = base as ApiParticipant;
  return {
    id: participant.user_id ?? fallbackId,
    name: base.name,
    email: base.email ?? `${fallbackId}@local.invalid`,
    avatar: base.avatar ?? undefined,
    role: normalizeRole(base.role),
    department: base.department ?? 'Genel',
  };
}

function mapAgendaItem(item: ApiAgendaItem, index: number): AgendaItem {
  return {
    id: item.id ?? `agenda-${index + 1}`,
    title: item.title,
    duration: item.duration,
    completed: Boolean(item.completed),
  };
}

function mapRecording(recording?: ApiRecording): MeetingRecording | undefined {
  if (!recording) {
    return undefined;
  }
  return {
    status: recording.status,
    mode: recording.mode ?? undefined,
    startedAt: recording.started_at ?? undefined,
    stoppedAt: recording.stopped_at ?? undefined,
    readyAt: recording.ready_at ?? undefined,
    filesCount: recording.files_count,
    archivePath: recording.archive_path ?? undefined,
  };
}

function mapAnalysisInfo(analysis?: ApiAnalysisInfo): MeetingAnalysisInfo | undefined {
  if (!analysis) {
    return undefined;
  }
  return {
    status: analysis.status,
    generatedAt: analysis.generated_at ?? undefined,
    segmentCount: analysis.segment_count ?? 0,
    summaryCount: analysis.summary_count ?? 0,
  };
}

function mapParticipant(participant: ApiParticipant, index: number): MeetingParticipant {
  return {
    user: mapUser(participant, participant.participant_id ?? `participant-${index + 1}`),
    status: participant.status ?? participant.response_status ?? 'pending',
    joinedAt: participant.joined_at ? new Date(participant.joined_at) : undefined,
    leftAt: participant.left_at ? new Date(participant.left_at) : undefined,
    speakingTime: participant.speaking_time ?? undefined,
    cameraOnTime: participant.camera_on_time ?? undefined,
    micOnTime: participant.mic_on_time ?? undefined,
  };
}

export function mapApiMeeting(meeting: ApiMeeting): Meeting {
  const organizer = mapUser(meeting.organizer, `organizer-${meeting.id}`);
  return {
    id: meeting.id,
    title: meeting.title,
    description: meeting.description ?? undefined,
    startTime: new Date(meeting.scheduled_start),
    endTime: new Date(meeting.scheduled_end),
    status: meeting.status,
    organizer,
    participants: meeting.participants.map(mapParticipant),
    agenda: meeting.agenda.map(mapAgendaItem),
    sessionId: meeting.session_id ?? null,
    recording: mapRecording(meeting.recording),
    analysis: mapAnalysisInfo(meeting.analysis),
  };
}

export function mergeMeetingAnalysis(meeting: Meeting, analysis: ApiMeetingAnalysis): Meeting {
  const timeline: MeetingTimelineSegment[] = analysis.timeline.map((item) => ({
    id: String(item.segment_id),
    type: item.type,
    overlap: item.overlap,
    startTime: item.start_sec,
    endTime: item.end_sec,
    duration: item.duration_sec,
    startAt: item.start_at ?? undefined,
    endAt: item.end_at ?? undefined,
    participants: item.participants.map((participant) => ({
      participantId: participant.participant_id,
      displayName: participant.display_name,
    })),
  }));

  const speakingDistribution: MeetingAnalytics['speakingDistribution'] = analysis.analytics.speaking_distribution.map(
    (item) => ({
      userId: item.participant_id ?? item.display_name,
      userName: item.display_name,
      percentage: item.percentage,
      duration: item.duration_sec,
    }),
  );

  const aiAnalytics: MeetingAnalytics | undefined =
    analysis.status === 'ready'
      ? {
          totalParticipants: analysis.analytics.total_participants,
          averageAttendance: analysis.analytics.average_attendance,
          speakingDistribution,
          engagementScore: analysis.analytics.engagement_score ?? 0,
          sentimentBreakdown: {
            positive: analysis.analytics.sentiment_breakdown?.positive ?? 0,
            neutral: analysis.analytics.sentiment_breakdown?.neutral ?? 0,
            negative: analysis.analytics.sentiment_breakdown?.negative ?? 0,
          },
        }
      : undefined;

  return {
    ...meeting,
    sessionId: analysis.session_id ?? meeting.sessionId ?? null,
    recording: mapRecording(analysis.recording) ?? meeting.recording,
    analysis: {
      status: analysis.status,
      generatedAt: analysis.generated_at ?? undefined,
      segmentCount: analysis.timeline.length,
      summaryCount: analysis.speaking_summary.length,
    },
    aiAnalytics,
    timeline,
  };
}

export async function listMeetings(query?: { status?: string; q?: string }): Promise<Meeting[]> {
  const params = new URLSearchParams();
  if (query?.status) params.set('status', query.status);
  if (query?.q) params.set('q', query.q);
  const suffix = params.toString();
  const response = await request<{ meetings: ApiMeeting[] }>(`/api/meetings${suffix ? `?${suffix}` : ''}`);
  return response.meetings.map(mapApiMeeting);
}

export async function getMeeting(meetingId: string): Promise<Meeting> {
  const response = await request<ApiMeeting>(`/api/meetings/${meetingId}`);
  return mapApiMeeting(response);
}

export async function createMeeting(input: CreateMeetingRequest): Promise<Meeting> {
  const response = await request<ApiMeeting>('/api/meetings', {
    method: 'POST',
    body: JSON.stringify({
      title: input.title,
      description: input.description,
      scheduled_start: input.scheduledStart,
      scheduled_end: input.scheduledEnd,
      organizer: {
        user_id: input.organizer.id,
        name: input.organizer.name,
        email: input.organizer.email,
        role: input.organizer.role,
        department: input.organizer.department,
        avatar: input.organizer.avatar,
      },
      participants: input.participants.map((participant) => ({
        user_id: participant.userId,
        participant_type: participant.participantType,
        name: participant.name,
        email: participant.email,
        role: participant.role,
        department: participant.department,
        avatar: participant.avatar,
        response_status: 'pending',
      })),
      agenda: input.agenda.map((item) => ({
        title: item.title,
        duration: item.duration,
      })),
    }),
  });

  return mapApiMeeting(response);
}

export async function getMeetingAnalysis(meetingId: string): Promise<ApiMeetingAnalysis> {
  return request<ApiMeetingAnalysis>(`/api/meetings/${meetingId}/analysis`);
}

export async function startMeetingSession(meetingId: string): Promise<{ meeting_id: string; session_id: string; status: string }> {
  return request<{ meeting_id: string; session_id: string; status: string }>(
    `/api/meetings/${meetingId}/start-session`,
    {
      method: 'POST',
    },
  );
}
