import { X, Mic, MicOff, VideoOff, Pin, PinOff } from 'lucide-react';

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

export function ParticipantsPanel({ onClose, participants, onPinToggle }: ParticipantsPanelProps) {
  return (
    <div className="w-80 h-full bg-gray-900 border-l border-gray-800 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
        <h3 className="text-white font-medium">Katılımcılar ({participants.length})</h3>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-white p-1 rounded hover:bg-gray-800"
        >
          <X size={20} />
        </button>
      </div>

      {/* Participants List */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-4 space-y-2">
          {participants.map((participant) => (
            <div
              key={participant.id}
              className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-800 group"
            >
              {participant.imageUrl ? (
                <img
                  src={participant.imageUrl}
                  alt={participant.name}
                  className="w-10 h-10 rounded-full object-cover"
                />
              ) : (
                <div className="w-10 h-10 rounded-full bg-gray-700 text-white/90 flex items-center justify-center text-xs font-semibold">
                  {getInitials(participant.name)}
                </div>
              )}
              <div className="flex-1 min-w-0">
                <p className="text-white text-sm truncate">
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
                {!participant.isVideoOn && (
                  <VideoOff size={16} className="text-gray-400" />
                )}
                <button
                  type="button"
                  onClick={() => onPinToggle(participant.id)}
                  className={`opacity-100 md:opacity-0 md:group-hover:opacity-100 p-1 transition ${
                    participant.isPinned ? 'text-amber-300 hover:text-amber-200' : 'text-gray-400 hover:text-white'
                  }`}
                  title={participant.isPinned ? 'Sabitlemeyi kaldir' : 'Sabitle'}
                  aria-label={participant.isPinned ? `${participant.name} sabitlemesini kaldir` : `${participant.name} sabitle`}
                >
                  {participant.isPinned ? <PinOff size={16} /> : <Pin size={16} />}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Footer Actions */}
      <div className="p-4 border-t border-gray-800 space-y-2">
        <button className="w-full bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium">
          Katılımcı Davet Et
        </button>
        <button className="w-full bg-gray-800 hover:bg-gray-700 text-white px-4 py-2 rounded-lg text-sm font-medium">
          Tüm Katılımcıları Sustur
        </button>
      </div>
    </div>
  );
}
