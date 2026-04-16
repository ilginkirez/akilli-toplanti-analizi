import { useEffect, useState } from 'react';
import { ArrowLeft, ChevronRight, Shield, Users, Video } from 'lucide-react';

interface LobbyProps {
  onJoin: (sessionId: string, participantName: string) => void;
  isJoining: boolean;
  error: string | null;
  backendConnected: boolean;
  defaultSessionId?: string;
  defaultParticipantName?: string;
  lockSessionId?: boolean;
  meetingTitle?: string;
  onBack?: () => void;
}

export function Lobby({
  onJoin,
  isJoining,
  error,
  backendConnected,
  defaultSessionId = '',
  defaultParticipantName = '',
  lockSessionId = false,
  meetingTitle,
  onBack,
}: LobbyProps) {
  const [sessionId, setSessionId] = useState(defaultSessionId);
  const [participantName, setParticipantName] = useState(defaultParticipantName);

  useEffect(() => {
    setSessionId(defaultSessionId);
  }, [defaultSessionId]);

  useEffect(() => {
    setParticipantName(defaultParticipantName);
  }, [defaultParticipantName]);

  const handleJoin = () => {
    if (!sessionId.trim() || !participantName.trim()) {
      return;
    }

    onJoin(sessionId.trim(), participantName.trim());
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-gradient-to-br from-gray-950 via-gray-900 to-indigo-950 p-4">
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -right-24 -top-24 h-96 w-96 rounded-full bg-indigo-600/10 blur-3xl" />
        <div className="absolute -bottom-24 -left-24 h-96 w-96 rounded-full bg-cyan-600/10 blur-3xl" />
        <div className="absolute left-1/2 top-1/2 h-[600px] w-[600px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-blue-600/5 blur-3xl" />
      </div>

      <div className="relative w-full max-w-md">
        {onBack && (
          <button
            type="button"
            onClick={onBack}
            className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-white/80 backdrop-blur hover:bg-white/10"
          >
            <ArrowLeft size={16} />
            Toplanti detayina don
          </button>
        )}

        <div className="mb-8 text-center">
          <div className="mb-5 inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-cyan-500 shadow-lg shadow-indigo-500/30">
            <Video size={32} className="text-white" />
          </div>
          <h1 className="mb-2 text-3xl font-bold text-white">
            {meetingTitle || 'Meeting Analyzer'}
          </h1>
          <p className="text-sm text-gray-400">
            Tam ekran LiveKit toplanti odasina gecmeden once bilgilerinizi kontrol edin.
          </p>
        </div>

        <div className="mb-6 flex items-center justify-center gap-2">
          <div
            className={`h-2 w-2 animate-pulse rounded-full ${
              backendConnected
                ? 'bg-emerald-400 shadow-sm shadow-emerald-400/50'
                : 'bg-amber-400 shadow-sm shadow-amber-400/50'
            }`}
          />
          <span className="text-xs text-gray-500">
            {backendConnected ? 'Backend bagli' : 'Demo modu (backend yok)'}
          </span>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/5 p-6 shadow-2xl backdrop-blur-xl">
          {error && (
            <div className="mb-4 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">
              {error}
            </div>
          )}

          <div className="mb-4">
            <label className="mb-2 block text-xs font-medium uppercase tracking-wider text-gray-400">
              Oturum ID
            </label>
            <div className="relative">
              <Shield size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
              <input
                id="session-id-input"
                type="text"
                value={sessionId}
                onChange={(event) => setSessionId(event.target.value)}
                disabled={lockSessionId}
                placeholder="meeting-2026-04-03"
                className="w-full rounded-xl border border-white/10 bg-white/5 py-3 pl-10 pr-4 text-sm text-white placeholder-gray-600 transition-all focus:border-indigo-500/50 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 disabled:cursor-not-allowed disabled:opacity-70"
              />
            </div>
          </div>

          <div className="mb-5">
            <label className="mb-2 block text-xs font-medium uppercase tracking-wider text-gray-400">
              Adiniz
            </label>
            <div className="relative">
              <Users size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
              <input
                id="participant-name-input"
                type="text"
                value={participantName}
                onChange={(event) => setParticipantName(event.target.value)}
                placeholder="Ahmet"
                className="w-full rounded-xl border border-white/10 bg-white/5 py-3 pl-10 pr-4 text-sm text-white placeholder-gray-600 transition-all focus:border-indigo-500/50 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              />
            </div>
          </div>

          <div className="mb-6 rounded-xl border border-white/10 bg-white/5 p-4">
            <p className="text-sm leading-6 text-gray-200">
              Ayni oturum ID ile birden fazla cihaz toplantiya baglanabilir.
            </p>
            <p className="mt-2 text-xs leading-5 text-gray-500">
              Her baglanti icin ayri participant, connection ve stream bilgisi korunur.
            </p>
          </div>

          <button
            id="join-meeting-btn"
            onClick={handleJoin}
            disabled={isJoining || !sessionId.trim() || !participantName.trim()}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-cyan-600 py-3.5 text-sm font-medium text-white shadow-lg shadow-indigo-500/20 transition-all duration-300 hover:from-indigo-500 hover:to-cyan-500 hover:shadow-indigo-500/40 active:scale-[0.98] disabled:cursor-not-allowed disabled:from-gray-700 disabled:to-gray-700"
          >
            {isJoining ? (
              <>
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                <span>Baglaniyor...</span>
              </>
            ) : (
              <>
                <span>Toplantiya Katil</span>
                <ChevronRight size={16} />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
