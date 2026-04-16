/**
 * api.ts
 * ------
 * Backend API iletişim katmanı.
 * Meeting Analyzer backend'ine REST istekleri gönderir.
 */

function resolveApiBase() {
  const configured = import.meta.env.VITE_API_URL?.trim();
  if (configured) {
    return configured.replace(/\/$/, '');
  }

  if (typeof window === 'undefined') {
    return 'http://localhost:8000';
  }

  const hostname = window.location.hostname;
  const isLocalhost =
    hostname === 'localhost' ||
    hostname === '127.0.0.1' ||
    hostname === '[::1]';

  return isLocalhost ? 'http://localhost:8000' : '';
}

const API_BASE = resolveApiBase();

// ─── Types ──────────────────────────────────────────────────────────────────

export interface SessionInfo {
  session_id: string;
  status: string;
  participants: string[];
  created_at: string;
}

export interface ConnectionInfo {
  connection_id: string;
  participant_id: string;
  token: string;
  session_id: string;
}

export interface ParticipantInfo {
  participant_id: string;
  connection_id: string | null;
  stream_ids: string[];
  is_speaking: boolean;
}

export interface SessionDetail {
  session_id: string;
  status: string;
  participants: Record<string, ParticipantInfo>;
  connections: number;
  streams: number;
  created_at: string;
}

export interface SessionStopResult {
  session_id: string;
  status: string;
  duration_sec: number;
  dataset: Record<string, unknown>;
  events_path: string;
}

export interface HealthCheck {
  status: string;
  openvidu_connected: boolean;
  livekit_connected?: boolean;
  rtc_provider?: string;
  active_sessions: number;
  timestamp: string;
}

export interface JoinTokenResponse {
  token: string;
  ws_url: string;
  participant_id: string;
  session_id: string;
  connection_id?: string | null;
  provider?: string;
  server_data?: Record<string, unknown>;
  recording_status?: string | null;
  recording_id?: string | null;
}

// ─── API Functions ──────────────────────────────────────────────────────────

export async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = API_BASE ? `${API_BASE}${path}` : path;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API Error ${res.status}: ${text}`);
  }

  return res.json();
}

export async function uploadRequest<T>(path: string, body: FormData): Promise<T> {
  const url = API_BASE ? `${API_BASE}${path}` : path;
  const res = await fetch(url, {
    method: 'POST',
    body,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API Error ${res.status}: ${text}`);
  }

  return res.json();
}

/** Yeni oturum oluşturur */
export async function createSession(
  sessionId?: string,
  participants?: string[]
): Promise<SessionInfo> {
  return request('/api/sessions', {
    method: 'POST',
    body: JSON.stringify({
      session_id: sessionId || undefined,
      participants: participants || [],
    }),
  });
}

/** Katılımcı bağlantısı oluşturur ve token döndürür */
export async function createConnection(
  sessionId: string,
  participantId: string,
  role: string = 'PUBLISHER'
): Promise<ConnectionInfo> {
  return request(`/api/sessions/${sessionId}/connections`, {
    method: 'POST',
    body: JSON.stringify({
      participant_id: participantId,
      role,
    }),
  });
}

/** Oturum bilgilerini getirir */
export async function getSession(sessionId: string): Promise<SessionDetail> {
  return request(`/api/sessions/${sessionId}`);
}

/** Aktif oturumları listeler */
export async function listSessions(): Promise<{ sessions: SessionInfo[] }> {
  return request('/api/sessions');
}

/** Oturumu durdurur ve dataset üretir */
export async function stopSession(sessionId: string): Promise<SessionStopResult> {
  return request(`/api/sessions/${sessionId}/stop`, {
    method: 'POST',
  });
}

/** Frontend'den olay bildirir */
export async function postEvent(
  sessionId: string,
  eventType: string,
  participantId?: string,
  connectionId?: string,
  streamId?: string,
  metadata?: Record<string, unknown>
): Promise<{ status: string }> {
  return request(`/api/sessions/${sessionId}/events`, {
    method: 'POST',
    body: JSON.stringify({
      event_type: eventType,
      participant_id: participantId,
      connection_id: connectionId,
      stream_id: streamId,
      metadata,
    }),
  });
}

/** Konuşma olayı bildirir */
export async function postSpeakingEvent(
  sessionId: string,
  participantId: string,
  isSpeaking: boolean,
  connectionId?: string,
  streamId?: string
): Promise<{ status: string; overlap_active: boolean }> {
  return request(`/api/sessions/${sessionId}/speaking`, {
    method: 'POST',
    body: JSON.stringify({
      participant_id: participantId,
      is_speaking: isSpeaking,
      connection_id: connectionId,
      stream_id: streamId,
    }),
  });
}

/** Oturum olaylarını getirir */
export async function getEvents(
  sessionId: string,
  eventType?: string,
  participantId?: string
): Promise<{ events: Record<string, unknown>[]; count: number }> {
  const params = new URLSearchParams();
  if (eventType) params.set('event_type', eventType);
  if (participantId) params.set('participant_id', participantId);
  const qs = params.toString();
  return request(`/api/sessions/${sessionId}/events${qs ? `?${qs}` : ''}`);
}

/** Katılımcı listesini getirir */
export async function getParticipants(
  sessionId: string
): Promise<{ participants: ParticipantInfo[] }> {
  return request(`/api/sessions/${sessionId}/participants`);
}

/** Sistem durumu kontrolü */
export async function healthCheck(): Promise<HealthCheck> {
  return request('/api/health');
}

export async function registerParticipantConnection(
  participantId: string,
  payload: {
    session_id: string;
    connection_id: string;
    client_data?: Record<string, unknown>;
    server_data?: Record<string, unknown>;
    connected_at?: string;
  }
): Promise<{ status: string; participant_id: string }> {
  return request('/api/participants/register', {
    method: 'POST',
    body: JSON.stringify({
      participant_id: participantId,
      ...payload,
    }),
  });
}

export async function updateParticipantStream(
  participantId: string,
  payload: {
    session_id: string;
    connection_id: string;
    stream_id: string;
    has_audio?: boolean;
    has_video?: boolean;
    video_source?: string;
    media_type?: string;
    client_data?: Record<string, unknown>;
    server_data?: Record<string, unknown>;
  }
): Promise<{ status: string; participant_id: string }> {
  return request(`/api/participants/${participantId}/stream`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function leaveParticipant(
  participantId: string,
  payload: {
    session_id: string;
    connection_id?: string | null;
    reason?: string;
    left_at?: string;
  }
): Promise<{ status: string; participant_id: string }> {
  return request(`/api/participants/${participantId}/leave`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function uploadParticipantRecording(payload: {
  session_id: string;
  participant_id: string;
  connection_id?: string | null;
  stream_id?: string | null;
  started_at?: string | null;
  ended_at?: string | null;
  mime_type?: string | null;
  device_label?: string | null;
  file: Blob;
  filename?: string;
}): Promise<{
  status: string;
  session_id: string;
  participant_id: string;
  file_path: string;
  start_time_offset_ms: number;
  end_time_offset_ms: number | null;
}> {
  const form = new FormData();
  form.set('session_id', payload.session_id);
  form.set('participant_id', payload.participant_id);
  if (payload.connection_id) form.set('connection_id', payload.connection_id);
  if (payload.stream_id) form.set('stream_id', payload.stream_id);
  if (payload.started_at) form.set('started_at', payload.started_at);
  if (payload.ended_at) form.set('ended_at', payload.ended_at);
  if (payload.mime_type) form.set('mime_type', payload.mime_type);
  if (payload.device_label) form.set('device_label', payload.device_label);
  form.set(
    'file',
    payload.file,
    payload.filename || `participant-${payload.participant_id}.webm`,
  );

  return uploadRequest('/api/recordings/upload/local', form);
}
