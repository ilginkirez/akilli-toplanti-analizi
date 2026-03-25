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
    { id: 1, sender: 'Tracy Brooks', text: 'Merhaba herkese!', time: '10:23' },
    { id: 2, sender: 'Dale Clarke', text: 'Toplantı 10 dakika içinde başlayacak.', time: '10:25' },
    { id: 3, sender: 'Rosa Griffin', text: 'Hazırım!', time: '10:27' },
  ]);
  const [newMessage, setNewMessage] = useState('');

  const handleSendMessage = () => {
    if (newMessage.trim()) {
      const message: Message = {
        id: messages.length + 1,
        sender: 'Ben',
        text: newMessage,
        time: new Date().toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages([...messages, message]);
      setNewMessage('');
    }
  };

  return (
    <div className="w-80 h-full bg-gray-900 border-l border-gray-800 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
        <h3 className="text-white font-medium">Sohbet</h3>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-white p-1 rounded hover:bg-gray-800"
        >
          <X size={20} />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((message) => (
          <div key={message.id} className="space-y-1">
            <div className="flex items-baseline gap-2">
              <span className="text-blue-400 text-sm font-medium">{message.sender}</span>
              <span className="text-gray-500 text-xs">{message.time}</span>
            </div>
            <p className="text-gray-200 text-sm">{message.text}</p>
          </div>
        ))}
      </div>

      {/* Input */}
      <div className="p-4 border-t border-gray-800">
        <div className="flex gap-2">
          <input
            type="text"
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
            placeholder="Mesajınızı yazın..."
            className="flex-1 bg-gray-800 text-white px-3 py-2 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleSendMessage}
            className="bg-blue-600 hover:bg-blue-700 text-white p-2 rounded-lg"
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
