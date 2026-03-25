import { ReactNode } from 'react';

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
  className = '' 
}: ControlButtonProps) {
  const baseStyles = "flex flex-col items-center justify-center gap-1 min-w-[64px] h-14 md:h-16 rounded-xl cursor-pointer transition-all duration-200 group";
  
  let variantStyles = "";
  if (variant === 'danger') {
    variantStyles = "text-red-400 hover:bg-red-500/10 hover:text-red-300";
  } else if (isActive) {
    variantStyles = "bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 shadow-inner";
  } else {
    variantStyles = "text-gray-400 hover:text-gray-200 hover:bg-gray-800/60";
  }
  
  return (
    <button 
      onClick={onClick}
      className={`${baseStyles} ${variantStyles} ${className}`}
      title={label}
    >
      <div className={`transition-transform duration-200 ${isActive ? 'scale-110' : 'group-hover:scale-110 group-active:scale-95'}`}>
        {icon}
      </div>
      <span className="text-[10px] md:text-xs font-medium tracking-wide opacity-80 mt-0.5">{label}</span>
    </button>
  );
}
