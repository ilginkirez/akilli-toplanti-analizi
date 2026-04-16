import { useCallback, useEffect, useRef, useState } from 'react';
import {
  type AudioTrack as LiveKitAudioTrack,
  ConnectionState,
  Room,
  RoomEvent,
  Track,
  VideoPresets,
  type Participant as LiveKitParticipant,
  type VideoTrack as LiveKitVideoTrack,
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
  audioLevel: number;
  lastSpokeAt: number | null;
  stream: MediaStream | null;
  audioTrack: LiveKitAudioTrack | null;
  videoTrack: LiveKitVideoTrack | null;
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

type StreamCacheEntry = {
  audioTrack: MediaStreamTrack | null;
  videoTrack: MediaStreamTrack | null;
  stream: MediaStream | null;
};

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

function buildParticipantModel(
  participant: LiveKitParticipant,
  streamCache: Map<string, StreamCacheEntry>,
): Participant {
  const metadata = parseMetadata(participant.metadata);
  const audioPublication = participant.getTrackPublication(Track.Source.Microphone);
  const videoPublication =
    participant.getTrackPublication(Track.Source.Camera) ??
    participant.getTrackPublication(Track.Source.ScreenShare);

  const audioTrack = audioPublication?.audioTrack ?? null;
  const videoTrack = videoPublication?.videoTrack ?? null;
  const audioMediaTrack = audioTrack?.mediaStreamTrack ?? null;
  const videoMediaTrack = videoTrack?.mediaStreamTrack ?? null;
  const cacheKey = participant.identity;
  const cachedEntry = streamCache.get(cacheKey);
  let stream = cachedEntry?.stream ?? null;

  if (
    cachedEntry?.audioTrack !== audioMediaTrack ||
    cachedEntry?.videoTrack !== videoMediaTrack
  ) {
    const tracks = [audioMediaTrack, videoMediaTrack].filter(
      (track): track is MediaStreamTrack => track !== null,
    );
    stream = tracks.length > 0 ? new MediaStream(tracks) : null;
    streamCache.set(cacheKey, {
      audioTrack: audioMediaTrack,
      videoTrack: videoMediaTrack,
      stream,
    });
  }

  return {
    id: participant.identity,
    name:
      participant.name ||
      (metadata['display_name'] as string | undefined) ||
      participant.identity ||
      'Unknown',
    connectionId: participant.sid || null,
    streamId: videoPublication?.trackSid ?? audioPublication?.trackSid ?? null,
    isMuted: !participant.isMicrophoneEnabled || !audioMediaTrack,
    isVideoOn: participant.isCameraEnabled && Boolean(videoMediaTrack),
    isSpeaking: participant.isSpeaking,
    audioLevel: participant.audioLevel,
    lastSpokeAt: participant.lastSpokeAt?.getTime() ?? null,
    stream,
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

function pickRecordingMimeType(): string {
  if (typeof MediaRecorder === 'undefined') {
    return '';
  }

  const candidates = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/ogg;codecs=opus',
  ];

  return candidates.find((item) => MediaRecorder.isTypeSupported(item)) ?? '';
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
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const recordingTrackRef = useRef<MediaStreamTrack | null>(null);
  const recordedChunksRef = useRef<Blob[]>([]);
  const recordingStartedAtRef = useRef<string | null>(null);
  const streamCacheRef = useRef<Map<string, StreamCacheEntry>>(new Map());
  const activeSpeakerSyncTimeoutRef = useRef<number | null>(null);

  const syncRoomState = useCallback((room: Room) => {
    const activeParticipantIds = new Set<string>([
      room.localParticipant.identity,
      ...Array.from(room.remoteParticipants.values()).map((participant) => participant.identity),
    ]);

    for (const cachedParticipantId of streamCacheRef.current.keys()) {
      if (!activeParticipantIds.has(cachedParticipantId)) {
        streamCacheRef.current.delete(cachedParticipantId);
      }
    }

    const localParticipant = buildParticipantModel(room.localParticipant, streamCacheRef.current);
    const remoteParticipants = Array.from(room.remoteParticipants.values()).map((participant) =>
      buildParticipantModel(participant, streamCacheRef.current),
    );

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

  const syncSpeakingState = useCallback((room: Room) => {
    setState((current) => {
      if (current.remoteParticipants.length === 0) {
        return current;
      }

      let changed = false;
      const nextRemoteParticipants = current.remoteParticipants.map((participant) => {
        const liveParticipant = room.remoteParticipants.get(participant.id);
        if (!liveParticipant) {
          return participant;
        }

        const nextIsSpeaking = liveParticipant.isSpeaking;
        const nextAudioLevel = liveParticipant.audioLevel;
        const nextLastSpokeAt = liveParticipant.lastSpokeAt?.getTime() ?? participant.lastSpokeAt;

        if (
          participant.isSpeaking === nextIsSpeaking &&
          participant.audioLevel === nextAudioLevel &&
          participant.lastSpokeAt === nextLastSpokeAt
        ) {
          return participant;
        }

        changed = true;
        return {
          ...participant,
          isSpeaking: nextIsSpeaking,
          audioLevel: nextAudioLevel,
          lastSpokeAt: nextLastSpokeAt,
        };
      });

      if (!changed) {
        return current;
      }

      return {
        ...current,
        remoteParticipants: nextRemoteParticipants,
      };
    });
  }, []);

  useEffect(() => {
    api.healthCheck()
      .then(() => setState((current) => ({ ...current, backendConnected: true })))
      .catch(() => setState((current) => ({ ...current, backendConnected: false })));
  }, []);

  useEffect(() => {
    return () => {
      if (activeSpeakerSyncTimeoutRef.current !== null) {
        window.clearTimeout(activeSpeakerSyncTimeoutRef.current);
      }
    };
  }, []);

  const cleanupRoom = useCallback(() => {
    roomRef.current = null;
    sessionIdRef.current = null;
    participantIdRef.current = null;
    connectionIdRef.current = null;
    streamCacheRef.current.clear();
    if (activeSpeakerSyncTimeoutRef.current !== null) {
      window.clearTimeout(activeSpeakerSyncTimeoutRef.current);
      activeSpeakerSyncTimeoutRef.current = null;
    }
  }, []);

  const startLocalAudioRecording = useCallback(async (room: Room) => {
    if (typeof MediaRecorder === 'undefined' || mediaRecorderRef.current) {
      return;
    }

    const microphonePublication = room.localParticipant.getTrackPublication(Track.Source.Microphone);
    const mediaStreamTrack = microphonePublication?.audioTrack?.mediaStreamTrack;
    if (!mediaStreamTrack) {
      return;
    }

    const clonedTrack = mediaStreamTrack.clone();
    const mimeType = pickRecordingMimeType();
    const recorder = mimeType
      ? new MediaRecorder(new MediaStream([clonedTrack]), { mimeType })
      : new MediaRecorder(new MediaStream([clonedTrack]));

    recordedChunksRef.current = [];
    recordingTrackRef.current = clonedTrack;
    recordingStartedAtRef.current = new Date().toISOString();

    recorder.addEventListener('dataavailable', (event) => {
      if (event.data.size > 0) {
        recordedChunksRef.current.push(event.data);
      }
    });

    recorder.start(1000);
    mediaRecorderRef.current = recorder;
    setState((current) => ({ ...current, isRecording: true }));
  }, []);

  const stopAndUploadLocalAudioRecording = useCallback(async () => {
    const recorder = mediaRecorderRef.current;
    if (!recorder) {
      return;
    }

    const participantId = participantIdRef.current;
    const sessionId = sessionIdRef.current;
    const connectionId = connectionIdRef.current;
    const room = roomRef.current;
    const startedAt = recordingStartedAtRef.current;

    mediaRecorderRef.current = null;
    recordingStartedAtRef.current = null;

    const recordingTrack = recordingTrackRef.current;
    recordingTrackRef.current = null;

    const blob = await new Promise<Blob | null>((resolve) => {
      recorder.addEventListener(
        'stop',
        () => {
          const type = recorder.mimeType || 'audio/webm';
          const output =
            recordedChunksRef.current.length > 0
              ? new Blob(recordedChunksRef.current, { type })
              : null;
          recordedChunksRef.current = [];
          resolve(output);
        },
        { once: true },
      );

      if (recorder.state !== 'inactive') {
        recorder.stop();
      } else {
        resolve(null);
      }
    });

    if (recordingTrack) {
      recordingTrack.stop();
    }

    if (!blob || !participantId || !sessionId) {
      setState((current) => ({ ...current, isRecording: false }));
      return;
    }

    try {
      const microphonePublication =
        room?.localParticipant.getTrackPublication(Track.Source.Microphone) ?? null;
      await api.uploadParticipantRecording({
        session_id: sessionId,
        participant_id: participantId,
        connection_id: connectionId,
        stream_id: microphonePublication?.trackSid ?? connectionId ?? participantId,
        started_at: startedAt,
        ended_at: new Date().toISOString(),
        mime_type: blob.type || recorder.mimeType || 'audio/webm',
        device_label: navigator.userAgent,
        file: blob,
      });
    } catch (error) {
      console.warn('uploadParticipantRecording failed', error);
    } finally {
      setState((current) => ({ ...current, isRecording: false }));
    }
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

    try {
      await stopAndUploadLocalAudioRecording();
    } catch (error) {
      console.warn('stopAndUploadLocalAudioRecording failed', error);
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
  }, [cleanupRoom, stopAndUploadLocalAudioRecording]);

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
      audioCaptureDefaults: {
        autoGainControl: false,
        echoCancellation: false,
        noiseSuppression: false,
      },
      videoCaptureDefaults: {
        resolution: VideoPresets.h720.resolution,
      },
    });

    roomRef.current = room;
    isLeavingRef.current = false;

    const handleStateRefresh = () => syncRoomState(room);
    const handleActiveSpeakersRefresh = () => {
      if (activeSpeakerSyncTimeoutRef.current !== null) {
        return;
      }

      activeSpeakerSyncTimeoutRef.current = window.setTimeout(() => {
        activeSpeakerSyncTimeoutRef.current = null;
        syncSpeakingState(room);
      }, 180);
    };

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
      .on(RoomEvent.ActiveSpeakersChanged, handleActiveSpeakersRefresh)
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

      await startLocalAudioRecording(room);

      setState((current) => ({
        ...current,
        sessionId: response.session_id,
        status: 'active',
        isRecording: true,
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
  }, [cleanupRoom, startLocalAudioRecording, syncRoomState, syncSpeakingState]);

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
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
      if (recordingTrackRef.current) {
        recordingTrackRef.current.stop();
      }
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
