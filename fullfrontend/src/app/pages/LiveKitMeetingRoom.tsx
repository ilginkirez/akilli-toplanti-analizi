import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router';
import {
  ArrowLeft,
  ChevronUp,
  Circle,
  MessageSquare,
  Mic,
  MicOff,
  Settings,
  Share2,
  Shield,
  Users,
  Video,
  VideoOff,
} from 'lucide-react';

import { useAuth } from '../auth/AuthContext';
import { useMeetings } from '../meetings/MeetingsContext';
import { Lobby } from '../livekit-meeting/components/Lobby';
import { VideoParticipant } from '../livekit-meeting/components/VideoParticipant';
import { ControlButton } from '../livekit-meeting/components/ControlButton';
import { ViewModeDropdown, type ViewMode } from '../livekit-meeting/components/ViewModeDropdown';
import { ParticipantsPanel } from '../livekit-meeting/components/ParticipantsPanel';
import { ChatPanel } from '../livekit-meeting/components/ChatPanel';
import { type Participant, useMeeting } from '../livekit-meeting/hooks/useMeeting';

const ACTIVE_SPEAKER_SWITCH_DELAY_MS = 1800;
const ACTIVE_SPEAKER_AUDIO_THRESHOLD = 0.03;

function pickDominantRemoteSpeaker(participants: Participant[]): Participant | null {
  const eligibleParticipants = participants
    .filter(
      (participant) =>
        participant.isSpeaking &&
        !participant.isMuted &&
        participant.audioLevel >= ACTIVE_SPEAKER_AUDIO_THRESHOLD,
    )
    .sort((left, right) => {
      if (right.audioLevel !== left.audioLevel) {
        return right.audioLevel - left.audioLevel;
      }

      return (right.lastSpokeAt ?? 0) - (left.lastSpokeAt ?? 0);
    });

  return eligibleParticipants[0] ?? null;
}

export function LiveKitMeetingRoom() {
  const navigate = useNavigate();
  const { id } = useParams();
  const { user } = useAuth();
  const { getMeetingById } = useMeetings();
  const meetingState = useMeeting();
  const routeMeetingId = id ?? '';
  const meeting = getMeetingById(routeMeetingId);
  const meetingTitle = meeting?.title ?? 'Canli Toplanti';

  const [viewMode, setViewMode] = useState<ViewMode>('speaker');
  const [isParticipantsOpen, setIsParticipantsOpen] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [pinnedParticipantId, setPinnedParticipantId] = useState<string | null>(null);
  const [focusedParticipantId, setFocusedParticipantId] = useState<string | null>(null);
  const pendingSpeakerTimerRef = useRef<number | null>(null);
  const pendingSpeakerIdRef = useRef<string | null>(null);

  const { localParticipant, remoteParticipants } = meetingState;
  const allParticipants = useMemo(
    () => [localParticipant, ...remoteParticipants].filter(Boolean) as Participant[],
    [localParticipant, remoteParticipants],
  );
  const remoteCount = remoteParticipants.length;

  const handleBack = () => {
    navigate(meeting ? `/meetings/${meeting.id}` : '/meetings');
  };

  useEffect(() => {
    return () => {
      if (pendingSpeakerTimerRef.current !== null) {
        window.clearTimeout(pendingSpeakerTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!pinnedParticipantId) {
      return;
    }

    const pinnedStillExists = allParticipants.some((participant) => participant.id === pinnedParticipantId);
    if (!pinnedStillExists) {
      setPinnedParticipantId(null);
    }
  }, [allParticipants, pinnedParticipantId]);

  useEffect(() => {
    if (pinnedParticipantId) {
      if (pendingSpeakerTimerRef.current !== null) {
        window.clearTimeout(pendingSpeakerTimerRef.current);
        pendingSpeakerTimerRef.current = null;
      }
      pendingSpeakerIdRef.current = null;
      setFocusedParticipantId((current) => (current === pinnedParticipantId ? current : pinnedParticipantId));
      return;
    }

    if (remoteCount === 1) {
      if (pendingSpeakerTimerRef.current !== null) {
        window.clearTimeout(pendingSpeakerTimerRef.current);
        pendingSpeakerTimerRef.current = null;
      }
      pendingSpeakerIdRef.current = null;
      const directPeer = remoteParticipants[0];
      setFocusedParticipantId((current) => (current === directPeer.id ? current : directPeer.id));
      return;
    }

    if (remoteCount === 0) {
      if (pendingSpeakerTimerRef.current !== null) {
        window.clearTimeout(pendingSpeakerTimerRef.current);
        pendingSpeakerTimerRef.current = null;
      }
      pendingSpeakerIdRef.current = null;
      setFocusedParticipantId(localParticipant?.id ?? null);
      return;
    }

    const dominantRemoteSpeaker = pickDominantRemoteSpeaker(remoteParticipants);
    if (!dominantRemoteSpeaker) {
      if (pendingSpeakerTimerRef.current !== null) {
        window.clearTimeout(pendingSpeakerTimerRef.current);
        pendingSpeakerTimerRef.current = null;
      }
      pendingSpeakerIdRef.current = null;
      setFocusedParticipantId((current) => {
        const existingRemote = remoteParticipants.find((participant) => participant.id === current);
        if (existingRemote) {
          return current;
        }

        return remoteParticipants[0]?.id ?? null;
      });
      return;
    }

    setFocusedParticipantId((current) => {
      if (current === dominantRemoteSpeaker.id) {
        if (pendingSpeakerTimerRef.current !== null) {
          window.clearTimeout(pendingSpeakerTimerRef.current);
          pendingSpeakerTimerRef.current = null;
        }
        pendingSpeakerIdRef.current = null;
        return current;
      }

      const currentIsEligibleRemote = remoteParticipants.some((participant) => participant.id === current);
      if (!currentIsEligibleRemote) {
        return remoteParticipants[0]?.id ?? null;
      }

      if (pendingSpeakerIdRef.current === dominantRemoteSpeaker.id) {
        return current;
      }

      if (pendingSpeakerTimerRef.current !== null) {
        window.clearTimeout(pendingSpeakerTimerRef.current);
      }
      pendingSpeakerIdRef.current = dominantRemoteSpeaker.id;
      pendingSpeakerTimerRef.current = window.setTimeout(() => {
        setFocusedParticipantId((previous) =>
          previous === dominantRemoteSpeaker.id ? previous : dominantRemoteSpeaker.id,
        );
        pendingSpeakerIdRef.current = null;
        pendingSpeakerTimerRef.current = null;
      }, ACTIVE_SPEAKER_SWITCH_DELAY_MS);

      return current;
    });
  }, [localParticipant?.id, pinnedParticipantId, remoteCount, remoteParticipants]);

  const focusedParticipant =
    allParticipants.find((participant) => participant.id === focusedParticipantId) ??
    (remoteParticipants[0] ?? localParticipant);

  const togglePinnedParticipant = (participantId: string) => {
    setPinnedParticipantId((current) => (current === participantId ? null : participantId));
  };

  const speakerStripParticipants = remoteParticipants.filter(
    (participant) => participant.id !== focusedParticipant?.id,
  );
  const shouldShowLocalPreview =
    Boolean(localParticipant) && localParticipant?.id !== focusedParticipant?.id;

  if (!routeMeetingId) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-950 px-4 text-center text-white">
        <div>
          <p className="text-xl font-semibold">Toplanti odasi bulunamadi.</p>
          <button
            type="button"
            onClick={() => navigate('/meetings')}
            className="mt-4 rounded-xl bg-white px-4 py-2 font-medium text-gray-950"
          >
            Toplantilara Don
          </button>
        </div>
      </div>
    );
  }

  if (
    meetingState.status === 'idle' ||
    meetingState.status === 'joining' ||
    meetingState.status === 'ended'
  ) {
    return (
      <Lobby
        onJoin={meetingState.joinMeeting}
        isJoining={meetingState.status === 'joining'}
        error={meetingState.error}
        backendConnected={meetingState.backendConnected}
        defaultSessionId={routeMeetingId}
        defaultParticipantName={user?.name ?? ''}
        lockSessionId
        meetingTitle={meetingTitle}
        onBack={handleBack}
      />
    );
  }

  const renderVideoContent = () => {
    if (viewMode === 'gallery') {
      const count = allParticipants.length;
      let gridClass = 'grid-cols-1';
      if (count > 1) gridClass = 'grid-cols-2';
      if (count > 4) gridClass = 'grid-cols-3';
      if (count > 9) gridClass = 'grid-cols-4';

      return (
        <div className="flex flex-1 items-center justify-center p-4 md:p-6">
          <div className={`grid h-full max-h-[85vh] w-full max-w-7xl ${gridClass} auto-rows-fr gap-3 md:gap-4`}>
            {allParticipants.map((participant) => (
              <div key={participant.id} className="h-full w-full min-h-[200px]">
                <VideoParticipant
                  name={participant.name}
                  stream={participant.stream}
                  audioTrack={participant.audioTrack}
                  videoTrack={participant.videoTrack}
                  isMuted={participant.isMuted}
                  isVideoOn={participant.isVideoOn}
                  isSpeaking={participant.isSpeaking}
                  isLocal={participant.id === localParticipant?.id}
                  isPinned={participant.id === pinnedParticipantId}
                  showPinAction
                  onPinToggle={() => togglePinnedParticipant(participant.id)}
                />
              </div>
            ))}
          </div>
        </div>
      );
    }

    return (
      <div className="flex flex-1 flex-col gap-4 p-4 md:p-6">
        {speakerStripParticipants.length > 0 && (
          <div className="flex min-h-[140px] max-h-[160px] justify-center gap-3 overflow-x-auto pb-2 md:gap-4">
            {speakerStripParticipants.map((participant) => (
              <div key={participant.id} className="h-full w-48 flex-shrink-0">
                <VideoParticipant
                  name={participant.name}
                  stream={participant.stream}
                  audioTrack={participant.audioTrack}
                  videoTrack={participant.videoTrack}
                  isMuted={participant.isMuted}
                  isVideoOn={participant.isVideoOn}
                  isSpeaking={participant.isSpeaking}
                  isPinned={participant.id === pinnedParticipantId}
                  showPinAction
                  onPinToggle={() => togglePinnedParticipant(participant.id)}
                />
              </div>
            ))}
          </div>
        )}

        <div className="relative min-h-0 flex-1">
          <div className="flex h-full items-center justify-center">
            <div
              className="relative h-full w-full max-w-6xl overflow-hidden rounded-2xl bg-black shadow-2xl"
              style={{ contain: 'paint' }}
            >
              {focusedParticipant && (
                <VideoParticipant
                  key={focusedParticipant.id}
                  name={focusedParticipant.name}
                  stream={focusedParticipant.stream}
                  audioTrack={focusedParticipant.audioTrack}
                  videoTrack={focusedParticipant.videoTrack}
                  isMuted={focusedParticipant.isMuted}
                  isVideoOn={focusedParticipant.isVideoOn}
                  isSpeaking={focusedParticipant.isSpeaking}
                  isLocal={focusedParticipant.id === localParticipant?.id}
                  isLarge
                  isPinned={focusedParticipant.id === pinnedParticipantId}
                  showPinAction
                  onPinToggle={() => togglePinnedParticipant(focusedParticipant.id)}
                />
              )}
            </div>
          </div>

          {shouldShowLocalPreview && localParticipant && (
            <div
              className="absolute bottom-4 right-4 z-20 aspect-[4/3] w-32 overflow-hidden rounded-xl border border-white/15 bg-black sm:w-40 md:w-48"
              style={{ contain: 'paint', transform: 'translateZ(0)' }}
            >
              <VideoParticipant
                name={localParticipant.name}
                stream={localParticipant.stream}
                audioTrack={localParticipant.audioTrack}
                videoTrack={localParticipant.videoTrack}
                isMuted={localParticipant.isMuted}
                isVideoOn={localParticipant.isVideoOn}
                isSpeaking={localParticipant.isSpeaking}
                isLocal
                isPinned={localParticipant.id === pinnedParticipantId}
                showPinAction
                onPinToggle={() => togglePinnedParticipant(localParticipant.id)}
              />
            </div>
          )}
        </div>
      </div>
    );
  };

  const mappedParticipants = [localParticipant, ...remoteParticipants]
    .filter(Boolean)
    .map((participant) => ({
      id: participant!.id,
      name: participant!.name,
      imageUrl: '',
      isMuted: participant!.isMuted,
      isVideoOn: participant!.isVideoOn,
      isPinned: participant!.id === pinnedParticipantId,
      isLocal: participant!.id === localParticipant?.id,
    }));

  const handleLeaveMeeting = async () => {
    await meetingState.leaveMeeting();
    handleBack();
  };

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-gray-950 font-sans text-gray-100">
      <header className="z-10 flex h-16 flex-none items-center justify-between border-b border-gray-800 bg-gray-900/80 px-4 shadow-sm backdrop-blur-md">
        <div className="flex min-w-0 items-center gap-3">
          <button
            type="button"
            onClick={handleBack}
            className="flex h-10 w-10 items-center justify-center rounded-full border border-white/10 text-gray-300 transition hover:border-white/20 hover:bg-white/5 hover:text-white"
            aria-label="Toplanti detayina don"
          >
            <ArrowLeft size={18} />
          </button>
          <Shield size={18} className="hidden text-emerald-400 sm:block" />
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-gray-100">{meetingTitle}</p>
            <p className="truncate text-xs text-gray-400">
              Oturum: {meetingState.sessionId ?? routeMeetingId}
            </p>
          </div>
          {meetingState.connectionMessage && (
            <span className="rounded-full border border-sky-500/30 bg-sky-500/20 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-sky-200">
              {meetingState.connectionMessage}
            </span>
          )}
          {!meetingState.backendConnected && (
            <span className="rounded-full border border-amber-500/30 bg-amber-500/20 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-amber-300">
              Demo Modu
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <ViewModeDropdown currentMode={viewMode} onModeChange={setViewMode} />
        </div>
      </header>

      <main className="relative flex flex-1 overflow-hidden">
        <div className="flex flex-1 flex-col bg-black/40">{renderVideoContent()}</div>

        {isParticipantsOpen && (
          <div className="z-20 w-80 border-l border-gray-800 bg-gray-900/95 shadow-2xl backdrop-blur-xl transition-all duration-300">
            <ParticipantsPanel
              onClose={() => setIsParticipantsOpen(false)}
              participants={mappedParticipants}
              onPinToggle={togglePinnedParticipant}
            />
          </div>
        )}

        {isChatOpen && (
          <div className="z-20 w-80 border-l border-gray-800 bg-gray-900/95 shadow-2xl backdrop-blur-xl transition-all duration-300">
            <ChatPanel onClose={() => setIsChatOpen(false)} />
          </div>
        )}
      </main>

      <footer className="z-20 flex h-20 flex-none items-center justify-between border-t border-gray-800 bg-gray-900/95 px-4 shadow-[0_-4px_24px_-8px_rgba(0,0,0,0.5)] backdrop-blur-xl md:px-8">
        <div className="hidden items-center gap-1.5 rounded-2xl border border-gray-700/50 bg-gray-800/40 p-1.5 sm:flex md:gap-3">
          <div className="flex">
            <ControlButton
              icon={meetingState.isMuted ? <MicOff size={22} className="stroke-2" /> : <Mic size={22} className="stroke-2" />}
              label={meetingState.isMuted ? 'Sesi Ac' : 'Sessize Al'}
              onClick={meetingState.toggleMute}
              variant={meetingState.isMuted ? 'danger' : 'default'}
            />
            <button className="h-full rounded-r-xl px-1 text-gray-500 transition-colors hover:bg-gray-800 hover:text-gray-300">
              <ChevronUp size={14} />
            </button>
          </div>

          <div className="h-10 w-[1px] bg-gray-700/50" />

          <div className="flex">
            <ControlButton
              icon={meetingState.isVideoOn ? <Video size={22} className="stroke-2" /> : <VideoOff size={22} className="stroke-2" />}
              label={meetingState.isVideoOn ? 'Videoyu Durdur' : 'Videoyu Baslat'}
              onClick={meetingState.toggleVideo}
            />
            <button className="h-full rounded-r-xl px-1 text-gray-500 transition-colors hover:bg-gray-800 hover:text-gray-300">
              <ChevronUp size={14} />
            </button>
          </div>
        </div>

        <div className="mx-4 flex flex-1 items-center justify-center gap-2 overflow-x-auto no-scrollbar md:gap-4">
          <div className="flex gap-1 sm:hidden">
            <ControlButton
              icon={meetingState.isMuted ? <MicOff size={22} /> : <Mic size={22} />}
              label={meetingState.isMuted ? 'Sesi Ac' : 'Sessize Al'}
              onClick={meetingState.toggleMute}
              variant={meetingState.isMuted ? 'danger' : 'default'}
            />
            <ControlButton
              icon={meetingState.isVideoOn ? <Video size={22} /> : <VideoOff size={22} />}
              label={meetingState.isVideoOn ? 'Videoyu Durdur' : 'Videoyu Baslat'}
              onClick={meetingState.toggleVideo}
            />
          </div>

          <ControlButton
            icon={<Users size={20} />}
            label="Katilimcilar"
            onClick={() => {
              setIsParticipantsOpen((current) => !current);
              if (isChatOpen) {
                setIsChatOpen(false);
              }
            }}
            isActive={isParticipantsOpen}
          />
          <ControlButton
            icon={<MessageSquare size={20} />}
            label="Sohbet"
            onClick={() => {
              setIsChatOpen((current) => !current);
              if (isParticipantsOpen) {
                setIsParticipantsOpen(false);
              }
            }}
            isActive={isChatOpen}
          />
          <ControlButton icon={<Share2 size={20} />} label="Paylas" />
          <ControlButton
            icon={<Circle size={20} className={meetingState.isRecording ? 'text-red-400' : 'text-gray-400'} />}
            label={meetingState.isRecording ? 'Kayit Acik' : 'Kayit'}
            isActive={meetingState.isRecording}
          />
          <ControlButton icon={<Settings size={20} />} label="Ayarlar" className="hidden md:flex" />
        </div>

        <div className="flex items-center">
          <button
            onClick={handleLeaveMeeting}
            className="whitespace-nowrap rounded-xl bg-red-500 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-red-500/20 transition-all duration-200 hover:bg-red-600 active:bg-red-700 md:px-8"
          >
            Ayril
          </button>
        </div>
      </footer>
    </div>
  );
}
