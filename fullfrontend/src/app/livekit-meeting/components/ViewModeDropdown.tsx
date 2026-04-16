import { useEffect, useRef, useState } from 'react';
import { ChevronDown, Grid3x3, Monitor, User } from 'lucide-react';

export type ViewMode = 'speaker' | 'gallery' | 'screenShare';

interface ViewModeDropdownProps {
  currentMode: ViewMode;
  onModeChange: (mode: ViewMode) => void;
}

export function ViewModeDropdown({
  currentMode,
  onModeChange,
}: ViewModeDropdownProps) {
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
    { id: 'speaker' as ViewMode, label: 'Konusmaci Gorunumu', icon: <User size={18} /> },
    { id: 'gallery' as ViewMode, label: 'Galeri Gorunumu', icon: <Grid3x3 size={18} /> },
    { id: 'screenShare' as ViewMode, label: 'Ekran Paylasimi', icon: <Monitor size={18} /> },
  ];

  const currentModeLabel = modes.find((mode) => mode.id === currentMode)?.label ?? 'Gorunum';

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen((current) => !current)}
        className="flex items-center gap-2 rounded-lg bg-gray-800 px-3 py-2 text-sm text-white hover:bg-gray-700"
      >
        <span>{currentModeLabel}</span>
        <ChevronDown size={16} className={`transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute bottom-full right-0 mb-2 min-w-[200px] overflow-hidden rounded-lg border border-gray-700 bg-gray-800 shadow-lg">
          {modes.map((mode) => (
            <button
              key={mode.id}
              onClick={() => {
                onModeChange(mode.id);
                setIsOpen(false);
              }}
              className={`flex w-full items-center gap-3 px-4 py-3 text-left transition-colors ${
                currentMode === mode.id ? 'bg-gray-700 text-blue-400' : 'text-white hover:bg-gray-700'
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
