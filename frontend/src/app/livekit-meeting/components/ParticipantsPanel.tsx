import { Mic, MicOff, Pin, PinOff, VideoOff, X } from 'lucide-react';

interface Participant {
  id: string;
  name: string;
  imageUrl: string;
  isMuted: boolean;
  isVideoOn: boolean;
  isPinned: boolean;
  isLocal: boolean;
}

interface ParticipantsPanelProps {
  onClose: () => void;
  participants: Participant[];
  onPinToggle: (participantId: string) => void;
}

function getInitials(name: string) {
  return name
    .split(' ')
    .map((part) => part[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

export function ParticipantsPanel({
  onClose,
  participants,
  onPinToggle,
}: ParticipantsPanelProps) {
  return (
    <div className="flex h-full w-80 flex-col border-l border-gray-800 bg-gray-900">
      <div className="flex items-center justify-between border-b border-gray-800 px-4 py-3">
        <h3 className="font-medium text-white">Katılımcılar ({participants.length})</h3>
        <button onClick={onClose} className="rounded p-1 text-gray-400 hover:bg-gray-800 hover:text-white">
          <X size={20} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <div className="space-y-2">
          {participants.map((participant) => (
            <div
              key={participant.id}
              className="group flex items-center gap-3 rounded-lg p-2 hover:bg-gray-800"
            >
              {participant.imageUrl ? (
                <img
                  src={participant.imageUrl}
                  alt={participant.name}
                  className="h-10 w-10 rounded-full object-cover"
                />
              ) : (
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gray-700 text-xs font-semibold text-white/90">
                  {getInitials(participant.name)}
                </div>
              )}

              <div className="min-w-0 flex-1">
                <p className="truncate text-sm text-white">
                  {participant.name}
                  {participant.isLocal ? ' (Sen)' : ''}
                </p>
              </div>

              <div className="flex items-center gap-2">
                {participant.isMuted ? (
                  <MicOff size={16} className="text-red-500" />
                ) : (
                  <Mic size={16} className="text-gray-400" />
                )}
                {!participant.isVideoOn && <VideoOff size={16} className="text-gray-400" />}
                <button
                  type="button"
                  onClick={() => onPinToggle(participant.id)}
                  className={`p-1 transition md:opacity-0 md:group-hover:opacity-100 ${
                    participant.isPinned ? 'text-amber-300 hover:text-amber-200' : 'text-gray-400 hover:text-white'
                  }`}
                  title={participant.isPinned ? 'Sabitlemeyi kaldır' : 'Sabitle'}
                  aria-label={
                    participant.isPinned
                      ? `${participant.name} sabitlemesini kaldır`
                      : `${participant.name} sabitle`
                  }
                >
                  {participant.isPinned ? <PinOff size={16} /> : <Pin size={16} />}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
