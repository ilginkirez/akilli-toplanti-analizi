import { useState } from 'react';
import { ChevronRight, Shield, Users, Video } from 'lucide-react';

interface LobbyProps {
  onJoin: (sessionId: string, participantName: string) => void;
  isJoining: boolean;
  error: string | null;
  backendConnected: boolean;
}

export function Lobby({ onJoin, isJoining, error, backendConnected }: LobbyProps) {
  const [sessionId, setSessionId] = useState('');
  const [participantName, setParticipantName] = useState('');

  const handleJoin = () => {
    if (!sessionId.trim() || !participantName.trim()) {
      return;
    }
    onJoin(sessionId.trim(), participantName.trim());
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-indigo-950 flex items-center justify-center p-4">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-24 -right-24 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl" />
        <div className="absolute -bottom-24 -left-24 w-96 h-96 bg-cyan-600/10 rounded-full blur-3xl" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-blue-600/5 rounded-full blur-3xl" />
      </div>

      <div className="relative w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-cyan-500 shadow-lg shadow-indigo-500/30 mb-5">
            <Video size={32} className="text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">Meeting Analyzer</h1>
          <p className="text-gray-400 text-sm">
            Multi-device participant capture with isolated microphone recordings
          </p>
        </div>

        <div className="flex items-center justify-center gap-2 mb-6">
          <div className={`w-2 h-2 rounded-full ${backendConnected ? 'bg-emerald-400 shadow-sm shadow-emerald-400/50' : 'bg-amber-400 shadow-sm shadow-amber-400/50'} animate-pulse`} />
          <span className="text-xs text-gray-500">
            {backendConnected ? 'Backend bagli' : 'Demo modu (backend yok)'}
          </span>
        </div>

        <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-2xl">
          {error && (
            <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-sm">
              {error}
            </div>
          )}

          <div className="mb-4">
            <label className="block text-gray-400 text-xs font-medium mb-2 uppercase tracking-wider">
              Oturum ID
            </label>
            <div className="relative">
              <Shield size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
              <input
                id="session-id-input"
                type="text"
                value={sessionId}
                onChange={(event) => setSessionId(event.target.value)}
                placeholder="meeting-2026-04-03"
                className="w-full bg-white/5 border border-white/10 text-white placeholder-gray-600 pl-10 pr-4 py-3 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 transition-all"
              />
            </div>
          </div>

          <div className="mb-5">
            <label className="block text-gray-400 text-xs font-medium mb-2 uppercase tracking-wider">
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
                className="w-full bg-white/5 border border-white/10 text-white placeholder-gray-600 pl-10 pr-4 py-3 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 transition-all"
              />
            </div>
          </div>

          <div className="mb-6 rounded-xl border border-white/10 bg-white/5 p-4">
            <p className="text-gray-200 text-sm leading-6">
              3-5 kisi ayni <span className="font-semibold text-white">Oturum ID</span> ile kendi cihazindan baglanabilir.
            </p>
            <p className="text-gray-500 text-xs mt-2 leading-5">
              Her baglanti icin ayri participant_id uretilir. Mikrofon kaydi individual modda alinip participant_id -&gt; connection_id -&gt; stream_id -&gt; recording zinciri korunur.
            </p>
          </div>

          <button
            id="join-meeting-btn"
            onClick={handleJoin}
            disabled={isJoining || !sessionId.trim() || !participantName.trim()}
            className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-indigo-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 disabled:from-gray-700 disabled:to-gray-700 disabled:cursor-not-allowed text-white py-3.5 rounded-xl font-medium text-sm transition-all duration-300 shadow-lg shadow-indigo-500/20 hover:shadow-indigo-500/40 active:scale-[0.98]"
          >
            {isJoining ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
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

        <div className="mt-6 text-center">
          <p className="text-gray-600 text-xs">
            Her kullanicinin mikrofonu ayri bir stream olarak kaydedilir.
          </p>
          <p className="text-gray-700 text-xs mt-1">
            participant_id -&gt; connection_id -&gt; stream_id -&gt; recording
          </p>
        </div>
      </div>
    </div>
  );
}
