export function LoadingSpinner({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-8 w-8',
    lg: 'h-12 w-12'
  };

  return (
    <div className="flex items-center justify-center">
      <div className={`${sizeClasses[size]} rounded-full border-2 border-gray-200 dark:border-gray-800 border-t-blue-600 animate-spin`} />
    </div>
  );
}
