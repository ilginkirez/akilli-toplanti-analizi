import { useEffect, useMemo, useRef, useState } from 'react';
import { type Participant, useMeeting } from './hooks/useMeeting';
import { Lobby } from './components/Lobby';
import { VideoParticipant } from './components/VideoParticipant';
import { ControlButton } from './components/ControlButton';
import { ViewModeDropdown, ViewMode } from './components/ViewModeDropdown';
import { ParticipantsPanel } from './components/ParticipantsPanel';
import { ChatPanel } from './components/ChatPanel';
import {
  Mic,
  MicOff,
  Video,
  VideoOff,
  Shield,
  Users,
  MessageSquare,
  Share2,
  Circle,
  Settings,
  ChevronUp,
} from 'lucide-react';

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

export default function App() {
  const meeting = useMeeting();

  const [viewMode, setViewMode] = useState<ViewMode>('speaker');
  const [isParticipantsOpen, setIsParticipantsOpen] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [pinnedParticipantId, setPinnedParticipantId] = useState<string | null>(null);
  const [focusedParticipantId, setFocusedParticipantId] = useState<string | null>(null);
  const pendingSpeakerTimerRef = useRef<number | null>(null);
  const pendingSpeakerIdRef = useRef<string | null>(null);

  // Active meeting screen
  const { localParticipant, remoteParticipants } = meeting;
  const allParticipants = useMemo(
    () => [localParticipant, ...remoteParticipants].filter(Boolean) as Participant[],
    [localParticipant, remoteParticipants],
  );
  const remoteCount = remoteParticipants.length;

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

  // If we are not in an active meeting, show the Lobby screen
  if (meeting.status === 'idle' || meeting.status === 'joining' || meeting.status === 'ended') {
    return (
      <Lobby
        onJoin={meeting.joinMeeting}
        isJoining={meeting.status === 'joining'}
        error={meeting.error}
        backendConnected={meeting.backendConnected}
      />
    );
  }

  const renderVideoContent = () => {
    if (viewMode === 'gallery') {
      // Calculate a good grid layout based on count
      const count = allParticipants.length;
      let gridClass = 'grid-cols-1';
      if (count > 1) gridClass = 'grid-cols-2';
      if (count > 4) gridClass = 'grid-cols-3';
      if (count > 9) gridClass = 'grid-cols-4';

      return (
        <div className="flex-1 p-4 md:p-6 flex items-center justify-center">
          <div className={`w-full h-full max-w-7xl max-h-[85vh] grid ${gridClass} gap-3 md:gap-4 auto-rows-fr`}>
            {allParticipants.map((p) => p && (
              <div key={p.id} className="w-full h-full min-h-[200px]">
                <VideoParticipant
                  name={p.name}
                  stream={p.stream}
                  audioTrack={p.audioTrack}
                  videoTrack={p.videoTrack}
                  isMuted={p.isMuted}
                  isVideoOn={p.isVideoOn}
                  isSpeaking={p.id === localParticipant?.id ? false : p.isSpeaking}
                  isLocal={p.id === localParticipant?.id}
                  isPinned={p.id === pinnedParticipantId}
                  showPinAction={true}
                  onPinToggle={() => togglePinnedParticipant(p.id)}
                />
              </div>
            ))}
          </div>
        </div>
      );
    } // End Gallery

    // Speaker View (Default)
    return (
      <div className="flex-1 flex flex-col p-4 md:p-6 gap-4">
        {/* Top Strip Thumbnails */}
        {speakerStripParticipants.length > 0 && (
          <div className="flex justify-center gap-3 md:gap-4 overflow-x-auto pb-2 min-h-[140px] max-h-[160px]">
            {speakerStripParticipants.map((p) => (
              <div key={p.id} className="w-48 h-full flex-shrink-0">
                <VideoParticipant
                  name={p.name}
                  stream={p.stream}
                  audioTrack={p.audioTrack}
                  videoTrack={p.videoTrack}
                  isMuted={p.isMuted}
                  isVideoOn={p.isVideoOn}
                  isSpeaking={p.id === localParticipant?.id ? false : p.isSpeaking}
                  isPinned={p.id === pinnedParticipantId}
                  showPinAction={true}
                  onPinToggle={() => togglePinnedParticipant(p.id)}
                />
              </div>
            ))}
          </div>
        )}

        {/* Main Speaker Video */}
        <div className="flex-1 flex items-center justify-center min-h-0">
          <div
            className="w-full h-full max-w-6xl rounded-2xl overflow-hidden shadow-2xl relative bg-black"
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
                isSpeaking={
                  focusedParticipant.id === localParticipant?.id
                    ? false
                    : focusedParticipant.isSpeaking
                }
                isLocal={focusedParticipant.id === localParticipant?.id}
                isLarge={true}
                isPinned={focusedParticipant.id === pinnedParticipantId}
                showPinAction={true}
                onPinToggle={() => togglePinnedParticipant(focusedParticipant.id)}
              />
            )}
            {shouldShowLocalPreview && localParticipant && (
              <div
                className="absolute bottom-4 right-4 z-10 w-32 sm:w-40 md:w-48 aspect-[4/3] rounded-xl overflow-hidden border border-white/15 shadow-xl bg-black"
                style={{ contain: 'paint' }}
              >
                <VideoParticipant
                  name={localParticipant.name}
                  stream={localParticipant.stream}
                  audioTrack={localParticipant.audioTrack}
                  videoTrack={localParticipant.videoTrack}
                  isMuted={localParticipant.isMuted}
                  isVideoOn={localParticipant.isVideoOn}
                  isSpeaking={false}
                  isLocal={true}
                  isPinned={localParticipant.id === pinnedParticipantId}
                  showPinAction={true}
                  onPinToggle={() => togglePinnedParticipant(localParticipant.id)}
                />
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  // Convert participants to the format expected by the ParticipantsPanel
  const mappedParticipants = [localParticipant, ...remoteParticipants]
    .filter(Boolean)
    .map(p => ({
      id: p!.id,
      name: p!.name,
      imageUrl: '', // We don't have images in the real participants yet, using avatar initials
      isMuted: p!.isMuted,
      isVideoOn: p!.isVideoOn,
      isPinned: p!.id === pinnedParticipantId,
      isLocal: p!.id === localParticipant?.id,
    }));

  return (
    <div className="h-screen bg-gray-950 flex flex-col overflow-hidden text-gray-100 font-sans">
      {/* Top Header Layer */}
      <header className="flex-none h-14 bg-gray-900/80 backdrop-blur-md border-b border-gray-800 flex items-center justify-between px-4 z-10 shadow-sm">
        <div className="flex items-center gap-3">
          <Shield size={18} className="text-emerald-400" />
          <span className="text-sm font-semibold tracking-wide text-gray-200">
            {meeting.sessionId}
          </span>
          {meeting.connectionMessage && (
            <span className="px-2 py-0.5 rounded-full bg-sky-500/20 text-sky-200 text-[10px] font-bold tracking-wider uppercase border border-sky-500/30">
              {meeting.connectionMessage}
            </span>
          )}
          {!meeting.backendConnected && (
            <span className="px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 text-[10px] font-bold tracking-wider uppercase border border-amber-500/30">
              Demo Modu
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <ViewModeDropdown currentMode={viewMode} onModeChange={setViewMode} />
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 flex overflow-hidden relative">
        <div className="flex-1 flex flex-col bg-black/40">
          {renderVideoContent()}
        </div>

        {/* Side Panels */}
        {isParticipantsOpen && (
          <div className="w-80 border-l border-gray-800 bg-gray-900/95 backdrop-blur-xl shadow-2xl z-20 transition-all duration-300">
             <ParticipantsPanel
              onClose={() => setIsParticipantsOpen(false)}
              participants={mappedParticipants}
              onPinToggle={togglePinnedParticipant}
             />
          </div>
        )}
        {isChatOpen && (
           <div className="w-80 border-l border-gray-800 bg-gray-900/95 backdrop-blur-xl shadow-2xl z-20 transition-all duration-300">
             <ChatPanel onClose={() => setIsChatOpen(false)} />
           </div>
        )}
      </main>

      {/* Bottom Control Bar Layer */}
      <footer className="flex-none h-20 bg-gray-900/95 backdrop-blur-xl border-t border-gray-800 flex items-center px-4 md:px-8 justify-between z-20 shadow-[0_-4px_24px_-8px_rgba(0,0,0,0.5)]">
        
        {/* Left Side (AV Controls) */}
        <div className="flex items-center gap-1.5 md:gap-3 bg-gray-800/40 p-1.5 rounded-2xl border border-gray-700/50 hidden sm:flex">
          <div className="flex">
            <ControlButton
              icon={meeting.isMuted ? <MicOff size={22} className="stroke-2" /> : <Mic size={22} className="stroke-2" />}
              label={meeting.isMuted ? "Sesi Aç" : "Sessize Al"}
              onClick={meeting.toggleMute}
              variant={meeting.isMuted ? "danger" : "default"}
            />
            <button className="h-full px-1 text-gray-500 hover:text-gray-300 hover:bg-gray-800 rounded-r-xl transition-colors">
              <ChevronUp size={14} />
            </button>
          </div>
          
          <div className="w-[1px] h-10 bg-gray-700/50" />
          
          <div className="flex">
            <ControlButton
              icon={meeting.isVideoOn ? <Video size={22} className="stroke-2" /> : <VideoOff size={22} className="stroke-2" />}
              label={meeting.isVideoOn ? "Videoyu Durdur" : "Videoyu Başlat"}
              onClick={meeting.toggleVideo}
            />
             <button className="h-full px-1 text-gray-500 hover:text-gray-300 hover:bg-gray-800 rounded-r-xl transition-colors">
              <ChevronUp size={14} />
            </button>
          </div>
        </div>

        {/* Center Side (Meeting Controls) */}
        <div className="flex items-center gap-2 md:gap-4 overflow-x-auto no-scrollbar justify-center flex-1 mx-4">
           {/* Mobile AV controls */}
           <div className="sm:hidden flex gap-1">
             <ControlButton
                icon={meeting.isMuted ? <MicOff size={22} /> : <Mic size={22} />}
                label={meeting.isMuted ? "Sesi Aç" : "Sessize Al"}
                onClick={meeting.toggleMute}
                variant={meeting.isMuted ? "danger" : "default"}
              />
              <ControlButton
                icon={meeting.isVideoOn ? <Video size={22} /> : <VideoOff size={22} />}
                label={meeting.isVideoOn ? "Videoyu Durdur" : "Videoyu Başlat"}
                onClick={meeting.toggleVideo}
              />
           </div>

          <ControlButton
            icon={<Users size={20} />}
            label="Katılımcılar"
            onClick={() => {
              setIsParticipantsOpen(!isParticipantsOpen);
              if (isChatOpen) setIsChatOpen(false);
            }}
            isActive={isParticipantsOpen}
          />
          <ControlButton
            icon={<MessageSquare size={20} />}
            label="Sohbet"
            onClick={() => {
              setIsChatOpen(!isChatOpen);
              if (isParticipantsOpen) setIsParticipantsOpen(false);
            }}
            isActive={isChatOpen}
          />
          <ControlButton
            icon={<Share2 size={20} />}
            label="Paylaş"
          />
          <ControlButton
            icon={<Circle size={20} className={meeting.isRecording ? 'text-red-400' : 'text-gray-400'} />} 
            label={meeting.isRecording ? 'Kayit Acik' : 'Kayit'} 
            isActive={meeting.isRecording}
          />
          <ControlButton 
            icon={<Settings size={20} />} 
            label="Ayarlar" 
            className="hidden md:flex" 
          />
        </div>

        {/* Right Side (End Meeting) */}
        <div className="flex items-center">
          <button 
            onClick={meeting.leaveMeeting}
            className="bg-red-500 hover:bg-red-600 active:bg-red-700 text-white px-5 md:px-8 py-2.5 rounded-xl font-semibold text-sm transition-all duration-200 shadow-lg shadow-red-500/20 whitespace-nowrap"
          >
             Ayrıl
          </button>
        </div>
      </footer>
    </div>
  );
}
