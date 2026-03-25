import { useState, useRef, useEffect } from 'react';
import { Grid3x3, User, Monitor, ChevronDown } from 'lucide-react';

export type ViewMode = 'speaker' | 'gallery' | 'screenShare';

interface ViewModeDropdownProps {
  currentMode: ViewMode;
  onModeChange: (mode: ViewMode) => void;
}

export function ViewModeDropdown({ currentMode, onModeChange }: ViewModeDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const modes = [
    { id: 'speaker' as ViewMode, label: 'Konuşmacı Görünümü', icon: <User size={18} /> },
    { id: 'gallery' as ViewMode, label: 'Galeri Görünümü', icon: <Grid3x3 size={18} /> },
    { id: 'screenShare' as ViewMode, label: 'Ekran Paylaşımı', icon: <Monitor size={18} /> },
  ];

  const currentModeLabel = modes.find(m => m.id === currentMode)?.label || 'Görünüm';

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg text-sm"
      >
        <span>{currentModeLabel}</span>
        <ChevronDown size={16} className={`transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute bottom-full mb-2 right-0 bg-gray-800 border border-gray-700 rounded-lg shadow-lg overflow-hidden min-w-[200px]">
          {modes.map((mode) => (
            <button
              key={mode.id}
              onClick={() => {
                onModeChange(mode.id);
                setIsOpen(false);
              }}
              className={`w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-700 transition-colors ${
                currentMode === mode.id ? 'bg-gray-700 text-blue-400' : 'text-white'
              }`}
            >
              {mode.icon}
              <span className="text-sm">{mode.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
