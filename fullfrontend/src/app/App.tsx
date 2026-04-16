import { RouterProvider } from 'react-router';
import { router } from './routes';
import { ThemeProvider } from 'next-themes';
import { Toaster } from './components/ui/sonner';
import { AuthProvider } from './auth/AuthContext';
import { MeetingsProvider } from './meetings/MeetingsContext';

export default function App() {
  return (
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem>
      <AuthProvider>
        <MeetingsProvider>
          <RouterProvider router={router} />
          <Toaster />
        </MeetingsProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}
