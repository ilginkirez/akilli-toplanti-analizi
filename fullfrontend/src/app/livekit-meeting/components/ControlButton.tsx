import type { ReactNode } from 'react';

interface ControlButtonProps {
  icon: ReactNode;
  label: string;
  onClick?: () => void;
  variant?: 'default' | 'danger';
  isActive?: boolean;
  className?: string;
}

export function ControlButton({
  icon,
  label,
  onClick,
  variant = 'default',
  isActive,
  className = '',
}: ControlButtonProps) {
  const baseStyles =
    'group flex h-14 min-w-[64px] flex-col items-center justify-center gap-1 rounded-xl transition-all duration-200 md:h-16';

  let variantStyles = '';
  if (variant === 'danger') {
    variantStyles = 'text-red-400 hover:bg-red-500/10 hover:text-red-300';
  } else if (isActive) {
    variantStyles = 'border border-indigo-500/30 bg-indigo-500/20 text-indigo-400 shadow-inner';
  } else {
    variantStyles = 'text-gray-400 hover:bg-gray-800/60 hover:text-gray-200';
  }

  return (
    <button onClick={onClick} className={`${baseStyles} ${variantStyles} ${className}`} title={label}>
      <div
        className={`transition-transform duration-200 ${
          isActive ? 'scale-110' : 'group-hover:scale-110 group-active:scale-95'
        }`}
      >
        {icon}
      </div>
      <span className="mt-0.5 text-[10px] font-medium tracking-wide opacity-80 md:text-xs">
        {label}
      </span>
    </button>
  );
}
