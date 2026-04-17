import { createBrowserRouter, Navigate, useLocation } from 'react-router';
import { Layout } from './components/Layout';
import { Dashboard } from './pages/Dashboard';
import { Meetings } from './pages/Meetings';
import { MeetingDetail } from './pages/MeetingDetail';
import { CreateMeeting } from './pages/CreateMeeting';
import { Tasks } from './pages/Tasks';
import { Analytics } from './pages/Analytics';
import { NotFound } from './pages/NotFound';
import { Login } from './pages/Login';
import { LiveKitMeetingRoom } from './pages/LiveKitMeetingRoom';
import { useAuth } from './auth/AuthContext';

function AuthLoadingScreen() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50">
      <div className="rounded-2xl border border-slate-200 bg-white px-6 py-4 text-sm text-slate-600 shadow-sm">
        Oturum kontrol ediliyor...
      </div>
    </div>
  );
}

function getRedirectTarget(state: unknown) {
  if (
    state &&
    typeof state === 'object' &&
    'from' in state &&
    typeof (state as { from?: unknown }).from === 'string'
  ) {
    const target = (state as { from: string }).from;
    return target === '/login' ? '/' : target;
  }

  return '/';
}

function ProtectedLayoutRoute() {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <AuthLoadingScreen />;
  }

  if (!isAuthenticated) {
    const from = `${location.pathname}${location.search}${location.hash}`;
    return <Navigate to="/login" replace state={{ from }} />;
  }

  return <Layout />;
}

function ProtectedMeetingRoomRoute() {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <AuthLoadingScreen />;
  }

  if (!isAuthenticated) {
    const from = `${location.pathname}${location.search}${location.hash}`;
    return <Navigate to="/login" replace state={{ from }} />;
  }

  return <LiveKitMeetingRoom />;
}

function LoginRoute() {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <AuthLoadingScreen />;
  }

  if (isAuthenticated) {
    return <Navigate to={getRedirectTarget(location.state)} replace />;
  }

  return <Login />;
}

export const router = createBrowserRouter([
  {
    path: '/login',
    Component: LoginRoute,
  },
  {
    path: '/meeting-room/:id',
    Component: ProtectedMeetingRoomRoute,
  },
  {
    path: '/',
    Component: ProtectedLayoutRoute,
    children: [
      { index: true, Component: Dashboard },
      { path: 'meetings', Component: Meetings },
      { path: 'meetings/new', Component: CreateMeeting },
      { path: 'meetings/:id', Component: MeetingDetail },
      { path: 'tasks', Component: Tasks },
      { path: 'analytics', Component: Analytics },
      { path: '*', Component: NotFound }
    ]
  }
]);
