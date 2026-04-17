import { Outlet, NavLink, useLocation } from 'react-router';
import {
  LayoutDashboard,
  Calendar,
  CheckSquare,
  BarChart3,
  Plus,
  Moon,
  Sun,
  Bell,
  Search,
  Settings,
} from 'lucide-react';
import { useTheme } from 'next-themes';
import { useEffect, useState } from 'react';

import { Avatar, AvatarFallback, AvatarImage } from './ui/avatar';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';
import { useAuth } from '../auth/AuthContext';
import { getInitials } from '../utils/helpers';

export function Layout() {
  const { theme, setTheme } = useTheme();
  const { user, logout } = useAuth();
  const location = useLocation();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const navigation = [
    { name: 'Dashboard', href: '/', icon: LayoutDashboard },
    { name: 'Toplantılar', href: '/meetings', icon: Calendar },
    { name: 'Görevler', href: '/tasks', icon: CheckSquare },
    { name: 'Analitik', href: '/analytics', icon: BarChart3 },
  ];

  const isActive = (href: string) => {
    if (href === '/') {
      return location.pathname === '/';
    }

    return location.pathname.startsWith(href);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-gray-100 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950">
      <header className="sticky top-0 z-40 border-b border-gray-200 bg-white/80 backdrop-blur-xl dark:border-gray-800 dark:bg-gray-950/80">
        <div className="flex h-16 items-center gap-4 px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 shadow-lg shadow-blue-500/20">
              <Calendar className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-lg font-bold text-transparent">
                MeetingAI
              </h1>
              <p className="text-xs text-gray-500 dark:text-gray-400">Smart Meeting Platform</p>
            </div>
          </div>

          <div className="ml-8 max-w-xl flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <Input
                type="search"
                placeholder="Toplantı, görev veya kişi ara..."
                className="border-gray-200 bg-gray-50 pl-10 dark:border-gray-800 dark:bg-gray-900"
              />
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              className="rounded-full"
            >
              {mounted && theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
            </Button>

            <Button variant="ghost" size="icon" className="relative rounded-full">
              <Bell className="h-5 w-5" />
              <Badge className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center bg-red-500 p-0 text-xs text-white">
                3
              </Badge>
            </Button>

            <Button variant="ghost" size="icon" className="rounded-full">
              <Settings className="h-5 w-5" />
            </Button>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="gap-2 rounded-full px-2">
                  <Avatar className="h-8 w-8">
                    <AvatarImage src={user?.avatar} />
                    <AvatarFallback>{getInitials(user?.name || 'Kullanıcı')}</AvatarFallback>
                  </Avatar>
                  <span className="hidden text-sm md:inline">{user?.name}</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel>
                  <div className="flex flex-col">
                    <span>{user?.name}</span>
                    <span className="text-xs font-normal text-gray-500">{user?.email}</span>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem>Profil</DropdownMenuItem>
                <DropdownMenuItem>Ayarlar</DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem className="text-red-600" onClick={logout}>
                  Çıkış Yap
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </header>

      <div className="flex">
        <aside className="sticky top-16 h-[calc(100vh-4rem)] w-64 border-r border-gray-200 bg-white/50 backdrop-blur-sm dark:border-gray-800 dark:bg-gray-950/50">
          <nav className="flex flex-col gap-1 p-4">
            {navigation.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.href);

              return (
                <NavLink
                  key={item.href}
                  to={item.href}
                  className={`flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium transition-all ${
                    active
                      ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow-lg shadow-blue-500/20'
                      : 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800'
                  }`}
                >
                  <Icon className="h-5 w-5" />
                  {item.name}
                </NavLink>
              );
            })}

            <div className="my-4 border-t border-gray-200 dark:border-gray-800" />

            <NavLink
              to="/meetings/new"
              className="flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-green-500 to-emerald-600 px-4 py-3 text-sm font-medium text-white shadow-lg shadow-green-500/20 transition-all hover:shadow-xl hover:shadow-green-500/30"
            >
              <Plus className="h-5 w-5" />
              Yeni Toplantı
            </NavLink>
          </nav>

          <div className="absolute bottom-0 left-0 right-0 p-4">
            <div className="rounded-xl border border-blue-100 bg-gradient-to-br from-blue-50 to-purple-50 p-4 dark:border-blue-900 dark:from-blue-950/30 dark:to-purple-950/30">
              <div className="mb-2 flex items-center gap-2">
                <div className="h-2 w-2 animate-pulse rounded-full bg-green-500" />
                <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
                  Sistem Durumu
                </span>
              </div>
              <p className="text-xs text-gray-600 dark:text-gray-400">Tüm sistemler çalışıyor</p>
            </div>
          </div>
        </aside>

        <main className="flex-1 overflow-auto">
          <div className="p-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
