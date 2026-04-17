import { useState } from 'react';
import { Send, X } from 'lucide-react';

interface Message {
  id: number;
  sender: string;
  text: string;
  time: string;
}

interface ChatPanelProps {
  onClose: () => void;
}

export function ChatPanel({ onClose }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([
    { id: 1, sender: 'Sistem', text: 'Toplantı odasına hoş geldiniz.', time: '10:23' },
    { id: 2, sender: 'Host', text: 'Kamera ve mikrofon kontrolleri aşağıda yer alır.', time: '10:25' },
  ]);
  const [newMessage, setNewMessage] = useState('');

  const handleSendMessage = () => {
    if (!newMessage.trim()) {
      return;
    }

    setMessages((current) => [
      ...current,
      {
        id: current.length + 1,
        sender: 'Ben',
        text: newMessage.trim(),
        time: new Date().toLocaleTimeString('tr-TR', {
          hour: '2-digit',
          minute: '2-digit',
        }),
      },
    ]);
    setNewMessage('');
  };

  return (
    <div className="flex h-full w-80 flex-col border-l border-gray-800 bg-gray-900">
      <div className="flex items-center justify-between border-b border-gray-800 px-4 py-3">
        <h3 className="font-medium text-white">Sohbet</h3>
        <button onClick={onClose} className="rounded p-1 text-gray-400 hover:bg-gray-800 hover:text-white">
          <X size={20} />
        </button>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.map((message) => (
          <div key={message.id} className="space-y-1">
            <div className="flex items-baseline gap-2">
              <span className="text-sm font-medium text-blue-400">{message.sender}</span>
              <span className="text-xs text-gray-500">{message.time}</span>
            </div>
            <p className="text-sm text-gray-200">{message.text}</p>
          </div>
        ))}
      </div>

      <div className="border-t border-gray-800 p-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={newMessage}
            onChange={(event) => setNewMessage(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                handleSendMessage();
              }
            }}
            placeholder="Mesajınızı yazın..."
            className="flex-1 rounded-lg bg-gray-800 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button onClick={handleSendMessage} className="rounded-lg bg-blue-600 p-2 text-white hover:bg-blue-700">
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
