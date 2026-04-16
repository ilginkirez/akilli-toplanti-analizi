import { useEffect, useRef } from 'react';
import { Mic, MicOff, Pin, PinOff, VideoOff, User } from 'lucide-react';

interface VideoParticipantProps {
  name: string;
  stream?: MediaStream | null;
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

export function VideoParticipant({
  name,
  stream,
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

  useEffect(() => {
    if (!videoRef.current) {
      return;
    }

    const nextStream = stream && isVideoOn ? stream : null;
    if (videoRef.current.srcObject !== nextStream) {
      videoRef.current.srcObject = nextStream;
    }
  }, [stream, isVideoOn]);

  useEffect(() => {
    if (!audioRef.current) {
      return;
    }

    const hasAudioTrack = Boolean(stream && stream.getAudioTracks().length > 0);
    const nextStream = hasAudioTrack ? stream : null;
    if (audioRef.current.srcObject !== nextStream) {
      audioRef.current.srcObject = nextStream;
    }
  }, [stream]);

  useEffect(() => {
    return () => {
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
      if (audioRef.current) {
        audioRef.current.srcObject = null;
      }
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
    <div
      className={`relative w-full h-full rounded-xl overflow-hidden transition-all duration-300 ${
        isSpeaking
          ? 'ring-2 ring-emerald-400 shadow-lg shadow-emerald-400/20'
          : 'ring-1 ring-white/10'
      }`}
    >
      {!isLocal && <audio ref={audioRef} autoPlay playsInline />}

      {/* Video veya Avatar */}
      {stream && isVideoOn ? (
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted={isLocal}
          className={`w-full h-full ${isLarge ? 'object-contain bg-black' : 'object-cover'} ${isLocal ? '-scale-x-100' : ''}`}
        />
      ) : imageUrl && isVideoOn ? (
        <img
          src={imageUrl}
          alt={name}
          className="w-full h-full object-cover"
        />
      ) : (
        <div
          className="w-full h-full flex items-center justify-center"
          style={{
            background: `linear-gradient(135deg, hsl(${hue}, 40%, 15%) 0%, hsl(${hue}, 30%, 25%) 100%)`,
          }}
        >
          <div
            className={`rounded-full flex items-center justify-center font-semibold text-white/80 ${
              isLarge ? 'w-24 h-24 text-3xl' : 'w-12 h-12 text-base'
            }`}
            style={{
              background: `linear-gradient(135deg, hsl(${hue}, 50%, 35%) 0%, hsl(${hue}, 40%, 45%) 100%)`,
            }}
          >
            {initials || <User size={isLarge ? 36 : 20} />}
          </div>
        </div>
      )}

      {/* Speaking indicator pulse */}
      {isSpeaking && (
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute inset-0 border-2 border-emerald-400/30 rounded-xl animate-pulse" />
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
          <div className="flex items-center gap-2 min-w-0">
            {/* Speaking dot indicator */}
            {isSpeaking && (
              <div className="w-2 h-2 rounded-full bg-emerald-400 shadow-sm shadow-emerald-400/50 animate-pulse flex-shrink-0" />
            )}
            <span className="text-white text-xs font-medium truncate">
              {name}
              {isLocal ? ' (Sen)' : ''}
            </span>
          </div>
          <div className="flex items-center gap-1.5 flex-shrink-0">
            {isMuted ? (
              <div className="w-6 h-6 rounded-full bg-red-500/80 flex items-center justify-center">
                <MicOff size={12} className="text-white" />
              </div>
            ) : (
              <div
                className={`w-6 h-6 rounded-full flex items-center justify-center ${
                  isSpeaking ? 'bg-emerald-500/80' : 'bg-white/10'
                }`}
              >
                <Mic size={12} className="text-white" />
              </div>
            )}
            {!isVideoOn && (
              <div className="w-6 h-6 rounded-full bg-gray-500/80 flex items-center justify-center">
                <VideoOff size={12} className="text-white" />
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Local badge */}
      {isLocal && (
        <div className="absolute top-2 right-2 px-2 py-0.5 rounded-md bg-indigo-500/80 text-white text-[10px] font-medium">
          SEN
        </div>
      )}
    </div>
  );
}
