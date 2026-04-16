import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ConnectionState,
  Room,
  RoomEvent,
  Track,
  VideoPresets,
  type Participant as LiveKitParticipant,
} from 'livekit-client';

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
  connectionState: ConnectionState;
  connectionMessage: string | null;
}

function parseMetadata(metadata?: string): Record<string, unknown> {
  if (!metadata) {
    return {};
  }

  try {
    const parsed = JSON.parse(metadata);
    return typeof parsed === 'object' && parsed !== null ? (parsed as Record<string, unknown>) : {};
  } catch {
    return {};
  }
}

function buildParticipantModel(participant: LiveKitParticipant): Participant {
  const metadata = parseMetadata(participant.metadata);
  const audioPublication = participant.getTrackPublication(Track.Source.Microphone);
  const videoPublication =
    participant.getTrackPublication(Track.Source.Camera) ??
    participant.getTrackPublication(Track.Source.ScreenShare);

  const audioTrack = audioPublication?.audioTrack?.mediaStreamTrack ?? null;
  const videoTrack = videoPublication?.videoTrack?.mediaStreamTrack ?? null;
  const tracks = [audioTrack, videoTrack].filter(
    (track): track is MediaStreamTrack => track !== null,
  );

  return {
    id: participant.identity,
    name:
      participant.name ||
      (metadata['display_name'] as string | undefined) ||
      participant.identity ||
      'Unknown',
    connectionId: participant.sid || null,
    streamId: videoPublication?.trackSid ?? audioPublication?.trackSid ?? null,
    isMuted: !participant.isMicrophoneEnabled || !audioTrack,
    isVideoOn: participant.isCameraEnabled && Boolean(videoTrack),
    isSpeaking: participant.isSpeaking,
    stream: tracks.length > 0 ? new MediaStream(tracks) : null,
    audioTrack,
    videoTrack,
  };
}

function getDeviceInfo() {
  const ua = navigator.userAgent;
  return {
    browser: /Chrome/i.test(ua)
      ? 'chrome'
      : /Firefox/i.test(ua)
        ? 'firefox'
        : /Safari/i.test(ua)
          ? 'safari'
          : 'other',
    os:
      /Windows/i.test(ua)
        ? 'windows'
        : /Mac OS X/i.test(ua)
          ? 'macos'
          : /Android/i.test(ua)
            ? 'android'
            : /iPhone|iPad/i.test(ua)
              ? 'ios'
              : 'other',
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
    connectionState: ConnectionState.Disconnected,
    connectionMessage: null,
  });

  const roomRef = useRef<Room | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const participantIdRef = useRef<string | null>(null);
  const connectionIdRef = useRef<string | null>(null);
  const isLeavingRef = useRef(false);

  const syncRoomState = useCallback((room: Room) => {
    const localParticipant = buildParticipantModel(room.localParticipant);
    const remoteParticipants = Array.from(room.remoteParticipants.values()).map(buildParticipantModel);

    setState((current) => ({
      ...current,
      localParticipant,
      remoteParticipants,
      isMuted: localParticipant.isMuted,
      isVideoOn: localParticipant.isVideoOn,
      isScreenSharing: Boolean(
        room.localParticipant.getTrackPublication(Track.Source.ScreenShare)?.track,
      ),
      connectionState: room.state,
      connectionMessage:
        room.state === ConnectionState.Reconnecting ||
        room.state === ConnectionState.SignalReconnecting
          ? 'Baglanti yeniden kuruluyor...'
          : null,
    }));
  }, []);

  useEffect(() => {
    api.healthCheck()
      .then(() => setState((current) => ({ ...current, backendConnected: true })))
      .catch(() => setState((current) => ({ ...current, backendConnected: false })));
  }, []);

  const cleanupRoom = useCallback(() => {
    roomRef.current = null;
    sessionIdRef.current = null;
    participantIdRef.current = null;
    connectionIdRef.current = null;
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

    isLeavingRef.current = true;

    if (roomRef.current) {
      roomRef.current.disconnect();
    }

    cleanupRoom();

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
      connectionState: ConnectionState.Disconnected,
      connectionMessage: null,
    }));
  }, [cleanupRoom]);

  const joinMeeting = useCallback(async (sessionIdStr: string, participantName: string) => {
    setState((current) => ({
      ...current,
      status: 'joining',
      error: null,
      connectionState: ConnectionState.Connecting,
      connectionMessage: 'LiveKit baglantisi hazirlaniyor...',
    }));

    const room = new Room({
      adaptiveStream: true,
      dynacast: true,
      videoCaptureDefaults: {
        resolution: VideoPresets.h720.resolution,
      },
    });

    roomRef.current = room;
    isLeavingRef.current = false;

    const handleStateRefresh = () => syncRoomState(room);

    room
      .on(RoomEvent.Connected, () => {
        syncRoomState(room);
        setState((current) => ({
          ...current,
          status: 'active',
          connectionState: ConnectionState.Connected,
          connectionMessage: null,
        }));
      })
      .on(RoomEvent.ParticipantConnected, handleStateRefresh)
      .on(RoomEvent.ParticipantDisconnected, handleStateRefresh)
      .on(RoomEvent.TrackSubscribed, handleStateRefresh)
      .on(RoomEvent.TrackUnsubscribed, handleStateRefresh)
      .on(RoomEvent.TrackMuted, handleStateRefresh)
      .on(RoomEvent.TrackUnmuted, handleStateRefresh)
      .on(RoomEvent.LocalTrackPublished, handleStateRefresh)
      .on(RoomEvent.LocalTrackUnpublished, handleStateRefresh)
      .on(RoomEvent.ActiveSpeakersChanged, handleStateRefresh)
      .on(RoomEvent.ParticipantMetadataChanged, handleStateRefresh)
      .on(RoomEvent.ParticipantNameChanged, handleStateRefresh)
      .on(RoomEvent.ConnectionStateChanged, () => {
        setState((current) => ({
          ...current,
          connectionState: room.state,
        }));
        syncRoomState(room);
      })
      .on(RoomEvent.Reconnecting, () => {
        setState((current) => ({
          ...current,
          connectionState: ConnectionState.Reconnecting,
          connectionMessage: 'Medya baglantisi yeniden kuruluyor...',
        }));
      })
      .on(RoomEvent.SignalReconnecting, () => {
        setState((current) => ({
          ...current,
          connectionState: ConnectionState.SignalReconnecting,
          connectionMessage: 'Sinyallesme baglantisi yeniden kuruluyor...',
        }));
      })
      .on(RoomEvent.Reconnected, () => {
        syncRoomState(room);
        setState((current) => ({
          ...current,
          connectionState: ConnectionState.Connected,
          connectionMessage: null,
        }));
      })
      .on(RoomEvent.Disconnected, (reason) => {
        if (isLeavingRef.current) {
          return;
        }

        cleanupRoom();

        setState((current) => ({
          ...current,
          status: 'ended',
          localParticipant: null,
          remoteParticipants: [],
          connectionState: ConnectionState.Disconnected,
          connectionMessage: null,
          error: `LiveKit baglantisi kapandi${reason ? `: ${String(reason)}` : ''}`,
        }));
      });

    try {
      const response = await api.request<api.JoinTokenResponse>('/api/sessions/token', {
        method: 'POST',
        body: JSON.stringify({
          session_id: sessionIdStr,
          display_name: participantName,
          device_info: getDeviceInfo(),
        }),
      });

      participantIdRef.current = response.participant_id;
      sessionIdRef.current = response.session_id;

      room.prepareConnection(response.ws_url, response.token);
      await room.connect(response.ws_url, response.token);
      await room.localParticipant.setMicrophoneEnabled(true);
      await room.localParticipant.setCameraEnabled(true);

      connectionIdRef.current =
        room.localParticipant.sid || response.connection_id || response.participant_id;

      await api.registerParticipantConnection(response.participant_id, {
        session_id: response.session_id,
        connection_id: connectionIdRef.current,
        client_data: { display_name: participantName },
        server_data: response.server_data,
        connected_at: new Date().toISOString(),
      });

      syncRoomState(room);

      const cameraPublication = room.localParticipant.getTrackPublication(Track.Source.Camera);
      const microphonePublication = room.localParticipant.getTrackPublication(Track.Source.Microphone);
      const primaryTrackSid =
        cameraPublication?.trackSid ??
        microphonePublication?.trackSid ??
        connectionIdRef.current;

      await api.updateParticipantStream(response.participant_id, {
        session_id: response.session_id,
        connection_id: connectionIdRef.current,
        stream_id: primaryTrackSid,
        has_audio: Boolean(microphonePublication?.track),
        has_video: Boolean(cameraPublication?.track),
        video_source: cameraPublication?.track ? 'CAMERA' : 'NONE',
        media_type: 'livekit_participant',
        client_data: { display_name: participantName },
        server_data: response.server_data,
      });

      setState((current) => ({
        ...current,
        sessionId: response.session_id,
        status: 'active',
        isRecording: response.recording_status === 'started' || response.recording_status === 'starting',
        error: null,
        connectionState: ConnectionState.Connected,
        connectionMessage: null,
      }));
    } catch (error: any) {
      console.error(error);
      isLeavingRef.current = true;
      room.disconnect();
      cleanupRoom();

      setState((current) => ({
        ...current,
        status: 'idle',
        error: error.message || 'Toplantiya katilinamadi (LiveKit baglanti hatasi)',
        connectionState: ConnectionState.Disconnected,
        connectionMessage: null,
      }));
    }
  }, [cleanupRoom, syncRoomState]);

  const toggleMute = useCallback(() => {
    setState((current) => {
      const room = roomRef.current;
      if (!room || !current.localParticipant) {
        return current;
      }

      const nextMuted = !current.isMuted;
      void room.localParticipant.setMicrophoneEnabled(!nextMuted);

      return {
        ...current,
        isMuted: nextMuted,
        localParticipant: { ...current.localParticipant, isMuted: nextMuted },
      };
    });
  }, []);

  const toggleVideo = useCallback(() => {
    setState((current) => {
      const room = roomRef.current;
      if (!room || !current.localParticipant) {
        return current;
      }

      const nextVideoOn = !current.isVideoOn;
      void room.localParticipant.setCameraEnabled(nextVideoOn);

      return {
        ...current,
        isVideoOn: nextVideoOn,
        localParticipant: { ...current.localParticipant, isVideoOn: nextVideoOn },
      };
    });
  }, []);

  useEffect(() => {
    return () => {
      if (roomRef.current) {
        roomRef.current.disconnect();
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
