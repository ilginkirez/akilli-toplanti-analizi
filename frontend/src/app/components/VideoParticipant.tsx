import { memo, useEffect, useRef } from 'react';
import { Mic, MicOff, Pin, PinOff, VideoOff, User } from 'lucide-react';

interface VideoParticipantProps {
  name: string;
  stream?: MediaStream | null;
  videoTrack?: MediaStreamTrack | null;
  audioTrack?: MediaStreamTrack | null;
  imageUrl?: string;
  isMuted?: boolean;
  isVideoOn?: boolean;
  isSpeaking?: boolean;
  isLocal?: boolean;
  isLarge?: boolean;
  isPinned?: boolean;
  showPinAction?: boolean;
  onPinToggle?: () => void;
  pinLabel?: string;
}

function VideoParticipantComponent({
  name,
  stream,
  videoTrack,
  audioTrack,
  imageUrl,
  isMuted = false,
  isVideoOn = true,
  isSpeaking = false,
  isLocal = false,
  isLarge = false,
  isPinned = false,
  showPinAction = false,
  onPinToggle,
  pinLabel,
}: VideoParticipantProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const videoStreamRef = useRef<MediaStream | null>(null);
  const audioStreamRef = useRef<MediaStream | null>(null);
  const boundVideoTrackRef = useRef<MediaStreamTrack | null>(null);
  const boundAudioTrackRef = useRef<MediaStreamTrack | null>(null);

  const fallbackVideoTrack = videoTrack ?? stream?.getVideoTracks()[0] ?? null;
  const fallbackAudioTrack = audioTrack ?? stream?.getAudioTracks()[0] ?? null;
  const hasLiveVideoTrack = Boolean(
    fallbackVideoTrack && fallbackVideoTrack.readyState === 'live',
  );
  const hasLiveAudioTrack = Boolean(
    fallbackAudioTrack && fallbackAudioTrack.readyState === 'live',
  );
  const showVideo = hasLiveVideoTrack;
  const showVideoOffIndicator = !showVideo && !isVideoOn;
  const showSpeakingState = !isLocal && isSpeaking;

  useEffect(() => {
    if (!videoRef.current) {
      return;
    }

    if (!fallbackVideoTrack || fallbackVideoTrack.readyState !== 'live') {
      boundVideoTrackRef.current = null;
      videoStreamRef.current = null;
      if (videoRef.current.srcObject !== null) {
        videoRef.current.srcObject = null;
      }
      return;
    }

    if (boundVideoTrackRef.current !== fallbackVideoTrack) {
      boundVideoTrackRef.current = fallbackVideoTrack;
      videoStreamRef.current = new MediaStream([fallbackVideoTrack]);
    }

    if (videoRef.current.srcObject !== videoStreamRef.current) {
      videoRef.current.srcObject = videoStreamRef.current;
    }
  }, [fallbackVideoTrack]);

  useEffect(() => {
    if (!audioRef.current) {
      return;
    }

    if (!fallbackAudioTrack || fallbackAudioTrack.readyState !== 'live') {
      boundAudioTrackRef.current = null;
      audioStreamRef.current = null;
      if (audioRef.current.srcObject !== null) {
        audioRef.current.srcObject = null;
      }
      return;
    }

    if (boundAudioTrackRef.current !== fallbackAudioTrack) {
      boundAudioTrackRef.current = fallbackAudioTrack;
      audioStreamRef.current = new MediaStream([fallbackAudioTrack]);
    }

    if (audioRef.current.srcObject !== audioStreamRef.current) {
      audioRef.current.srcObject = audioStreamRef.current;
    }
  }, [fallbackAudioTrack]);

  useEffect(() => {
    return () => {
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
      if (audioRef.current) {
        audioRef.current.srcObject = null;
      }
      videoStreamRef.current = null;
      audioStreamRef.current = null;
      boundVideoTrackRef.current = null;
      boundAudioTrackRef.current = null;
    };
  }, []);

  const initials = name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);

  // Rastgele renk tonu (isimden turetilmis)
  const hue = name.split('').reduce((a, c) => a + c.charCodeAt(0), 0) % 360;

  return (
    <div className="relative isolate h-full w-full overflow-hidden rounded-xl bg-black ring-1 ring-white/10">
      {!isLocal && hasLiveAudioTrack && <audio ref={audioRef} autoPlay playsInline />}

      {/* Video veya Avatar */}
      {showVideo ? (
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted={isLocal}
          className={`h-full w-full transform-gpu ${isLarge ? 'object-contain bg-black' : 'object-cover'} ${isLocal ? '-scale-x-100' : ''}`}
          style={{ backfaceVisibility: 'hidden' }}
        />
      ) : imageUrl && isVideoOn ? (
        <img
          src={imageUrl}
          alt={name}
          className="h-full w-full object-cover"
        />
      ) : (
        <div
          className="flex h-full w-full items-center justify-center"
          style={{
            background: `linear-gradient(135deg, hsl(${hue}, 40%, 15%) 0%, hsl(${hue}, 30%, 25%) 100%)`,
          }}
        >
          <div
            className={`flex items-center justify-center rounded-full font-semibold text-white/80 ${
              isLarge ? 'h-24 w-24 text-3xl' : 'h-12 w-12 text-base'
            }`}
            style={{
              background: `linear-gradient(135deg, hsl(${hue}, 50%, 35%) 0%, hsl(${hue}, 40%, 45%) 100%)`,
            }}
          >
            {initials || <User size={isLarge ? 36 : 20} />}
          </div>
        </div>
      )}

      {/* Speaking indicator overlay */}
      <div
        className={`pointer-events-none absolute inset-0 rounded-xl border-2 transition-opacity duration-200 ${
          showSpeakingState
            ? 'border-[5px] border-emerald-400 opacity-100 shadow-[0_0_0_3px_rgba(34,197,94,0.55),0_0_38px_rgba(34,197,94,0.28),inset_0_0_0_1px_rgba(255,255,255,0.16)]'
            : 'border-transparent opacity-0'
        }`}
      />

      {showSpeakingState && (
        <div className="pointer-events-none absolute top-2 left-2 z-20 rounded-full border border-emerald-300/70 bg-emerald-400 px-2.5 py-1 text-[10px] font-black tracking-[0.18em] text-emerald-950 shadow-[0_10px_24px_rgba(34,197,94,0.32)]">
          KONUSUYOR
        </div>
      )}

      {showPinAction && onPinToggle && (
        <button
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            onPinToggle();
          }}
          className={`absolute top-2 left-2 z-10 flex items-center gap-1 rounded-full border px-2 py-1 text-[11px] font-medium transition ${
            isPinned
              ? 'border-amber-400/70 bg-amber-400/20 text-amber-100'
              : 'border-white/15 bg-black/45 text-white/85 hover:border-white/35 hover:bg-black/65'
          }`}
          aria-label={pinLabel ?? (isPinned ? `${name} sabitlemesini kaldir` : `${name} sabitle`)}
          title={pinLabel ?? (isPinned ? 'Sabitlemeyi kaldir' : 'Sabitle')}
        >
          {isPinned ? <PinOff size={12} /> : <Pin size={12} />}
          <span>{isPinned ? 'Pinli' : 'Pinle'}</span>
        </button>
      )}

      {/* Bottom overlay */}
      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent p-3">
        <div className="flex items-center justify-between">
          <div className="flex min-w-0 items-center gap-2">
            {/* Speaking dot indicator */}
            {showSpeakingState && (
              <div className="h-2 w-2 flex-shrink-0 animate-pulse rounded-full bg-emerald-400 shadow-sm shadow-emerald-400/50" />
            )}
            <span className="truncate text-xs font-medium text-white">
              {name}
              {isLocal ? ' (Sen)' : ''}
            </span>
          </div>
          <div className="flex flex-shrink-0 items-center gap-1.5">
            {isMuted ? (
              <div className="flex h-6 w-6 items-center justify-center rounded-full bg-red-500/80">
                <MicOff size={12} className="text-white" />
              </div>
            ) : (
              <div
                className={`flex h-6 w-6 items-center justify-center rounded-full ${
                  showSpeakingState ? 'bg-emerald-500/80' : 'bg-white/10'
                }`}
              >
                <Mic size={12} className="text-white" />
              </div>
            )}
            {showVideoOffIndicator && (
              <div className="flex h-6 w-6 items-center justify-center rounded-full bg-gray-500/80">
                <VideoOff size={12} className="text-white" />
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Local badge */}
      {isLocal && (
        <div className="absolute top-2 right-2 rounded-md bg-indigo-500/80 px-2 py-0.5 text-[10px] font-medium text-white">
          SEN
        </div>
      )}
    </div>
  );
}

function areEqual(
  prevProps: Readonly<VideoParticipantProps>,
  nextProps: Readonly<VideoParticipantProps>,
) {
  const ignoreSpeaking = prevProps.isLocal && nextProps.isLocal;

  return (
    prevProps.name === nextProps.name &&
    prevProps.stream === nextProps.stream &&
    prevProps.videoTrack === nextProps.videoTrack &&
    prevProps.audioTrack === nextProps.audioTrack &&
    prevProps.imageUrl === nextProps.imageUrl &&
    prevProps.isMuted === nextProps.isMuted &&
    prevProps.isVideoOn === nextProps.isVideoOn &&
    (ignoreSpeaking || prevProps.isSpeaking === nextProps.isSpeaking) &&
    prevProps.isLocal === nextProps.isLocal &&
    prevProps.isLarge === nextProps.isLarge &&
    prevProps.isPinned === nextProps.isPinned &&
    prevProps.showPinAction === nextProps.showPinAction &&
    prevProps.pinLabel === nextProps.pinLabel
  );
}

export const VideoParticipant = memo(VideoParticipantComponent, areEqual);
