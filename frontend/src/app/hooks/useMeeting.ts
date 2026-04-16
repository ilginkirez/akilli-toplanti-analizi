import { useCallback, useEffect, useRef, useState } from 'react';
import { OpenVidu, Publisher, Session } from 'openvidu-browser-v2compatibility';

import * as api from '../services/api';

export interface Participant {
  id: string;
  name: string;
  connectionId: string | null;
  streamId: string | null;
  isMuted: boolean;
  isVideoOn: boolean;
  isSpeaking: boolean;
  stream: MediaStream | null;
  audioTrack: MediaStreamTrack | null;
  videoTrack: MediaStreamTrack | null;
}

export interface MeetingState {
  sessionId: string | null;
  status: 'idle' | 'joining' | 'active' | 'ending' | 'ended';
  localParticipant: Participant | null;
  remoteParticipants: Participant[];
  isMuted: boolean;
  isVideoOn: boolean;
  isScreenSharing: boolean;
  isRecording: boolean;
  error: string | null;
  backendConnected: boolean;
}

interface ParsedConnectionData {
  participantId: string;
  displayName: string;
  clientData: Record<string, unknown>;
  serverData: Record<string, unknown>;
}

function parseConnectionData(raw: string, fallbackConnectionId: string): ParsedConnectionData {
  const [clientRaw = '', serverRaw = ''] = raw.split('%/%');

  const parsePart = (value: string): Record<string, unknown> => {
    if (!value) {
      return {};
    }
    try {
      const parsed = JSON.parse(value);
      return typeof parsed === 'object' && parsed !== null ? parsed as Record<string, unknown> : {};
    } catch {
      return { raw: value };
    }
  };

  const clientData = parsePart(clientRaw);
  const serverData = parsePart(serverRaw);
  const participantId =
    (serverData['participant_id'] as string | undefined) ??
    (clientData['participant_id'] as string | undefined) ??
    fallbackConnectionId;
  const displayName =
    (clientData['display_name'] as string | undefined) ??
    (serverData['display_name'] as string | undefined) ??
    (typeof clientData['raw'] === 'string' ? clientData['raw'] : undefined) ??
    'Unknown';

  return {
    participantId,
    displayName,
    clientData,
    serverData,
  };
}

function getDeviceInfo() {
  const ua = navigator.userAgent;
  return {
    browser: /Chrome/i.test(ua) ? 'chrome' : /Firefox/i.test(ua) ? 'firefox' : /Safari/i.test(ua) ? 'safari' : 'other',
    os:
      /Windows/i.test(ua) ? 'windows' :
      /Mac OS X/i.test(ua) ? 'macos' :
      /Android/i.test(ua) ? 'android' :
      /iPhone|iPad/i.test(ua) ? 'ios' :
      'other',
    device_type: /Mobi|Android/i.test(ua) ? 'mobile' : 'desktop',
  };
}

export function useMeeting() {
  const [state, setState] = useState<MeetingState>({
    sessionId: null,
    status: 'idle',
    localParticipant: null,
    remoteParticipants: [],
    isMuted: false,
    isVideoOn: true,
    isScreenSharing: false,
    isRecording: false,
    error: null,
    backendConnected: false,
  });

  const OV = useRef<OpenVidu | null>(null);
  const session = useRef<Session | null>(null);
  const publisherRef = useRef<Publisher | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const participantIdRef = useRef<string | null>(null);
  const connectionIdRef = useRef<string | null>(null);

  useEffect(() => {
    api.healthCheck()
      .then(() => setState((current) => ({ ...current, backendConnected: true })))
      .catch(() => setState((current) => ({ ...current, backendConnected: false })));
  }, []);

  const leaveMeeting = useCallback(async () => {
    setState((current) => ({ ...current, status: 'ending' }));

    const participantId = participantIdRef.current;
    const sessionId = sessionIdRef.current;
    const connectionId = connectionIdRef.current;

    if (participantId && sessionId) {
      try {
        await api.leaveParticipant(participantId, {
          session_id: sessionId,
          connection_id: connectionId,
          reason: 'client_leave',
          left_at: new Date().toISOString(),
        });
      } catch (error) {
        console.warn('leaveParticipant failed', error);
      }
    }

    if (session.current) {
      session.current.disconnect();
      session.current = null;
    }

    OV.current = null;
    publisherRef.current = null;
    sessionIdRef.current = null;
    participantIdRef.current = null;
    connectionIdRef.current = null;

    setState((current) => ({
      sessionId: null,
      status: 'ended',
      localParticipant: null,
      remoteParticipants: [],
      isMuted: false,
      isVideoOn: true,
      isScreenSharing: false,
      isRecording: false,
      error: null,
      backendConnected: current.backendConnected,
    }));
  }, []);

  const joinMeeting = useCallback(async (sessionIdStr: string, participantName: string) => {
    setState((current) => ({ ...current, status: 'joining', error: null }));

    try {
      OV.current = new OpenVidu();
      session.current = OV.current.initSession();

      session.current.on('streamCreated', (event) => {
        const subscriber = session.current!.subscribe(event.stream, undefined);
        const connectionData = parseConnectionData(
          event.stream.connection.data,
          event.stream.connection.connectionId,
        );
        const mediaStream = event.stream.getMediaStream();
        const audioTracks = mediaStream?.getAudioTracks() ?? [];
        const videoTracks = mediaStream?.getVideoTracks() ?? [];

        const newParticipant: Participant = {
          id: connectionData.participantId,
          name: connectionData.displayName,
          connectionId: event.stream.connection.connectionId,
          streamId: event.stream.streamId,
          isMuted: !event.stream.audioActive,
          isVideoOn: event.stream.videoActive,
          isSpeaking: false,
          stream: mediaStream ?? null,
          audioTrack: audioTracks[0] || null,
          videoTrack: videoTracks[0] || null,
        };

        setState((current) => {
          if (current.remoteParticipants.some((participant) => participant.id === newParticipant.id)) {
            return current;
          }
          return {
            ...current,
            remoteParticipants: [...current.remoteParticipants, newParticipant],
          };
        });

        subscriber.on('publisherStartSpeaking', () => {
          setState((current) => ({
            ...current,
            remoteParticipants: current.remoteParticipants.map((participant) =>
              participant.id === newParticipant.id ? { ...participant, isSpeaking: true } : participant
            ),
          }));
        });
        subscriber.on('publisherStopSpeaking', () => {
          setState((current) => ({
            ...current,
            remoteParticipants: current.remoteParticipants.map((participant) =>
              participant.id === newParticipant.id ? { ...participant, isSpeaking: false } : participant
            ),
          }));
        });
      });

      session.current.on('streamDestroyed', (event) => {
        const connectionData = parseConnectionData(
          event.stream.connection.data,
          event.stream.connection.connectionId,
        );
        setState((current) => ({
          ...current,
          remoteParticipants: current.remoteParticipants.filter(
            (participant) => participant.id !== connectionData.participantId,
          ),
        }));
      });

      const deviceInfo = getDeviceInfo();

      const response = await api.request<api.JoinTokenResponse>('/api/sessions/token', {
        method: 'POST',
        body: JSON.stringify({
          session_id: sessionIdStr,
          display_name: participantName,
          device_info: deviceInfo,
        }),
      });

      participantIdRef.current = response.participant_id;
      sessionIdRef.current = response.session_id;

      const clientData = {
        participant_id: response.participant_id,
        display_name: participantName,
      };

      await session.current.connect(response.token, clientData);

      connectionIdRef.current = session.current.connection.connectionId;

      await api.registerParticipantConnection(response.participant_id, {
        session_id: response.session_id,
        connection_id: session.current.connection.connectionId,
        client_data: clientData,
        server_data: response.server_data,
        connected_at: new Date().toISOString(),
      });

      const publisher = await OV.current.initPublisherAsync(undefined, {
        audioSource: undefined,
        videoSource: undefined,
        publishAudio: true,
        publishVideo: true,
        resolution: '1280x720',
        frameRate: 30,
        insertMode: 'APPEND',
        mirror: false,
      });

      publisherRef.current = publisher;
      await session.current.publish(publisher);

      publisher.on('publisherStartSpeaking', () => {
        setState((current) =>
          current.localParticipant
            ? {
                ...current,
                localParticipant: { ...current.localParticipant, isSpeaking: true },
              }
            : current
        );
      });
      publisher.on('publisherStopSpeaking', () => {
        setState((current) =>
          current.localParticipant
            ? {
                ...current,
                localParticipant: { ...current.localParticipant, isSpeaking: false },
              }
            : current
        );
      });

      const mediaStream = publisher.stream.getMediaStream();
      const audioTracks = mediaStream?.getAudioTracks() ?? [];
      const videoTracks = mediaStream?.getVideoTracks() ?? [];

      await api.updateParticipantStream(response.participant_id, {
        session_id: response.session_id,
        connection_id: session.current.connection.connectionId,
        stream_id: publisher.stream.streamId,
        has_audio: true,
        has_video: true,
        video_source: 'CAMERA',
        media_type: 'publisher',
        client_data: clientData,
        server_data: response.server_data,
      });

      const localParticipant: Participant = {
        id: response.participant_id,
        name: participantName,
        connectionId: session.current.connection.connectionId,
        streamId: publisher.stream.streamId,
        isMuted: false,
        isVideoOn: true,
        isSpeaking: false,
        stream: mediaStream ?? null,
        audioTrack: audioTracks[0] || null,
        videoTrack: videoTracks[0] || null,
      };

      setState((current) => ({
        ...current,
        sessionId: response.session_id,
        status: 'active',
        localParticipant,
        isRecording: response.recording_status === 'started' || response.recording_status === 'starting',
        error: null,
      }));
    } catch (error: any) {
      console.error(error);
      setState((current) => ({
        ...current,
        status: 'idle',
        error: error.message || 'Toplantiya katilinamadi (OpenVidu baglanti hatasi)',
      }));
    }
  }, []);

  const toggleMute = useCallback(() => {
    setState((current) => {
      if (!publisherRef.current || !current.localParticipant) {
        return current;
      }

      const nextMuted = !current.isMuted;
      publisherRef.current.publishAudio(!nextMuted);
      return {
        ...current,
        isMuted: nextMuted,
        localParticipant: { ...current.localParticipant, isMuted: nextMuted },
      };
    });
  }, []);

  const toggleVideo = useCallback(() => {
    setState((current) => {
      if (!publisherRef.current || !current.localParticipant) {
        return current;
      }

      const nextVideoOn = !current.isVideoOn;
      publisherRef.current.publishVideo(nextVideoOn);
      return {
        ...current,
        isVideoOn: nextVideoOn,
        localParticipant: { ...current.localParticipant, isVideoOn: nextVideoOn },
      };
    });
  }, []);

  useEffect(() => {
    return () => {
      if (session.current) {
        session.current.disconnect();
      }
    };
  }, []);

  return {
    ...state,
    joinMeeting,
    leaveMeeting,
    toggleMute,
    toggleVideo,
  };
}
