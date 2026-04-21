export interface User {
  id: string;
  name: string;
  email: string;
  avatar?: string;
  role: 'admin' | 'manager' | 'member';
  department: string;
  companyId?: string;
  companyCode?: string;
  companyName?: string;
  accountType?: 'company_member' | 'independent';
  status?: string;
}

export interface Meeting {
  id: string;
  title: string;
  description?: string;
  startTime: Date;
  endTime: Date;
  status: 'upcoming' | 'in-progress' | 'completed' | 'cancelled';
  organizer: User;
  participants: MeetingParticipant[];
  agenda: AgendaItem[];
  transcript?: Transcript;
  aiSummary?: AISummary;
  aiAnalytics?: MeetingAnalytics;
  recordingUrl?: string;
  sessionId?: string | null;
  recording?: MeetingRecording;
  analysis?: MeetingAnalysisInfo;
  timeline?: MeetingTimelineSegment[];
}

export interface MeetingParticipant {
  user: User;
  status: 'accepted' | 'pending' | 'declined';
  joinedAt?: Date;
  leftAt?: Date;
  speakingTime?: number; // in seconds
  cameraOnTime?: number; // in seconds
  micOnTime?: number; // in seconds
}

export interface AgendaItem {
  id: string;
  title: string;
  duration: number; // in minutes
  completed: boolean;
}

export interface Transcript {
  id?: string;
  meetingId?: string;
  segments: MeetingTranscriptSegment[] | SpeechSegment[];
  fullText?: string;
  generatedAt?: string;
}

export interface SpeechSegment {
  id: string;
  speaker: User;
  text: string;
  startTime: number; // seconds from meeting start
  endTime: number;
  sentiment?: 'positive' | 'neutral' | 'negative';
  confidence: number;
}

export interface MeetingTranscriptSegment {
  speaker: string;
  startTime: number;
  endTime: number;
  text: string;
}

export interface MeetingTimelineParticipant {
  participantId?: string;
  displayName: string;
}

export interface MeetingTimelineSegment {
  id: string;
  type: 'single' | 'overlap';
  overlap: boolean;
  startTime: number;
  endTime: number;
  duration: number;
  participants: MeetingTimelineParticipant[];
  startAt?: string;
  endAt?: string;
}

export interface AISummary {
  executiveSummary: string;
  keyDecisions: string[];
  actionItems: MeetingActionItem[] | Task[];
  topics: string[];
  sentiment?: 'positive' | 'neutral' | 'negative';
  agendaAdherence?: number; // 0-100 percentage
}

export interface MeetingActionItem {
  id: string;
  title: string;
  description?: string;
  assigneeId?: string;
  dueDate?: string;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  needsReview?: boolean;
}

export interface MeetingAnalytics {
  totalParticipants: number;
  averageAttendance: number; // percentage
  speakingDistribution: {
    userId: string;
    userName: string;
    percentage: number;
    duration: number;
  }[];
  engagementScore: number; // 0-100
  sentimentBreakdown: {
    positive: number;
    neutral: number;
    negative: number;
  };
}

export interface MeetingRecording {
  status: string;
  mode?: string;
  startedAt?: string;
  stoppedAt?: string;
  readyAt?: string;
  filesCount?: number;
  archivePath?: string;
}

export interface MeetingAnalysisInfo {
  status: string;
  generatedAt?: string;
  segmentCount: number;
  summaryCount: number;
  aiStatus?: string;
  transcriptAvailable?: boolean;
}

export interface Task {
  id: string;
  title: string;
  description?: string;
  assignee: User;
  assigner?: User;
  dueDate: Date;
  status: 'todo' | 'in-progress' | 'completed' | 'overdue';
  priority: 'low' | 'medium' | 'high' | 'urgent';
  sourceType: 'manual' | 'ai-generated';
  meetingId?: string;
  createdAt: Date;
  completedAt?: Date;
  tags: string[];
}

export interface PerformanceMetrics {
  userId: string;
  user: User;
  period: {
    start: Date;
    end: Date;
  };
  tasksAssigned: number;
  tasksCompleted: number;
  tasksOverdue: number;
  completionRate: number; // percentage
  meetingsAttended: number;
  meetingsScheduled: number;
  attendanceRate: number; // percentage
  averageSpeakingTime: number; // percentage across all meetings
  productivityScore: number; // 0-100
  workloadStatus: 'underloaded' | 'balanced' | 'overloaded';
}

export interface TeamAnalytics {
  period: {
    start: Date;
    end: Date;
  };
  totalMeetings: number;
  totalTasks: number;
  completedTasks: number;
  overdueTasks: number;
  teamProductivityScore: number;
  bottlenecks: {
    userId: string;
    userName: string;
    issue: string;
    severity: 'low' | 'medium' | 'high';
  }[];
  topPerformers: {
    userId: string;
    userName: string;
    score: number;
  }[];
}
