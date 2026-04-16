import { format, formatDistanceToNow, isToday, isTomorrow, isThisWeek, isPast, isFuture } from 'date-fns';
import { tr } from 'date-fns/locale';

export function formatDate(date: Date | string, formatStr: string = 'PPP'): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  return format(dateObj, formatStr, { locale: tr });
}

export function formatTime(date: Date | string): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  return format(dateObj, 'HH:mm');
}

export function formatDateTime(date: Date | string): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  return format(dateObj, 'PPP HH:mm', { locale: tr });
}

export function getRelativeTime(date: Date | string): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  
  if (isToday(dateObj)) {
    return `Bugün ${formatTime(dateObj)}`;
  }
  
  if (isTomorrow(dateObj)) {
    return `Yarın ${formatTime(dateObj)}`;
  }
  
  if (isThisWeek(dateObj)) {
    return format(dateObj, 'EEEE HH:mm', { locale: tr });
  }
  
  return formatDistanceToNow(dateObj, { addSuffix: true, locale: tr });
}

export function getMeetingStatusColor(status: string): string {
  switch (status) {
    case 'upcoming':
      return 'bg-blue-500/10 text-blue-600 dark:text-blue-400';
    case 'in-progress':
      return 'bg-green-500/10 text-green-600 dark:text-green-400';
    case 'completed':
      return 'bg-gray-500/10 text-gray-600 dark:text-gray-400';
    case 'cancelled':
      return 'bg-red-500/10 text-red-600 dark:text-red-400';
    default:
      return 'bg-gray-500/10 text-gray-600 dark:text-gray-400';
  }
}

export function getMeetingStatusLabel(status: string): string {
  switch (status) {
    case 'upcoming':
      return 'Yaklaşan';
    case 'in-progress':
      return 'Devam Ediyor';
    case 'completed':
      return 'Tamamlandı';
    case 'cancelled':
      return 'İptal Edildi';
    default:
      return status;
  }
}

export function getTaskStatusColor(status: string): string {
  switch (status) {
    case 'todo':
      return 'bg-gray-500/10 text-gray-600 dark:text-gray-400';
    case 'in-progress':
      return 'bg-blue-500/10 text-blue-600 dark:text-blue-400';
    case 'completed':
      return 'bg-green-500/10 text-green-600 dark:text-green-400';
    case 'overdue':
      return 'bg-red-500/10 text-red-600 dark:text-red-400';
    default:
      return 'bg-gray-500/10 text-gray-600 dark:text-gray-400';
  }
}

export function getTaskStatusLabel(status: string): string {
  switch (status) {
    case 'todo':
      return 'Yapılacak';
    case 'in-progress':
      return 'Devam Ediyor';
    case 'completed':
      return 'Tamamlandı';
    case 'overdue':
      return 'Gecikmiş';
    default:
      return status;
  }
}

export function getPriorityColor(priority: string): string {
  switch (priority) {
    case 'urgent':
      return 'bg-red-500/10 text-red-600 dark:text-red-400 border-red-200 dark:border-red-800';
    case 'high':
      return 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-200 dark:border-orange-800';
    case 'medium':
      return 'bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 border-yellow-200 dark:border-yellow-800';
    case 'low':
      return 'bg-green-500/10 text-green-600 dark:text-green-400 border-green-200 dark:border-green-800';
    default:
      return 'bg-gray-500/10 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-800';
  }
}

export function getPriorityLabel(priority: string): string {
  switch (priority) {
    case 'urgent':
      return 'Acil';
    case 'high':
      return 'Yüksek';
    case 'medium':
      return 'Orta';
    case 'low':
      return 'Düşük';
    default:
      return priority;
  }
}

export function getWorkloadStatusColor(status: string): string {
  switch (status) {
    case 'underloaded':
      return 'text-blue-600 dark:text-blue-400';
    case 'balanced':
      return 'text-green-600 dark:text-green-400';
    case 'overloaded':
      return 'text-red-600 dark:text-red-400';
    default:
      return 'text-gray-600 dark:text-gray-400';
  }
}

export function getWorkloadStatusLabel(status: string): string {
  switch (status) {
    case 'underloaded':
      return 'Düşük Kapasite';
    case 'balanced':
      return 'Dengeli';
    case 'overloaded':
      return 'Aşırı Yük';
    default:
      return status;
  }
}

export function getSentimentColor(sentiment: string): string {
  switch (sentiment) {
    case 'positive':
      return 'text-green-600 dark:text-green-400';
    case 'neutral':
      return 'text-gray-600 dark:text-gray-400';
    case 'negative':
      return 'text-red-600 dark:text-red-400';
    default:
      return 'text-gray-600 dark:text-gray-400';
  }
}

export function getSentimentLabel(sentiment: string): string {
  switch (sentiment) {
    case 'positive':
      return 'Pozitif';
    case 'neutral':
      return 'Nötr';
    case 'negative':
      return 'Negatif';
    default:
      return sentiment;
  }
}

export function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  
  if (hours > 0) {
    return `${hours}s ${minutes}dk`;
  }
  if (minutes > 0) {
    return `${minutes}dk ${secs}sn`;
  }
  return `${secs}sn`;
}

export function getScoreColor(score: number): string {
  if (score >= 90) return 'text-green-600 dark:text-green-400';
  if (score >= 75) return 'text-blue-600 dark:text-blue-400';
  if (score >= 60) return 'text-yellow-600 dark:text-yellow-400';
  return 'text-red-600 dark:text-red-400';
}

export function getInitials(name: string): string {
  return name
    .split(' ')
    .map(n => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

export function cn(...classes: (string | undefined | null | boolean)[]): string {
  return classes.filter(Boolean).join(' ');
}
