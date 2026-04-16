import { useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router';
import { Calendar, LockKeyhole, Mail, UserRound } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { mockUsers } from '../data/mockData';
import { useAuth } from '../auth/AuthContext';

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

export function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();
  const demoUser = mockUsers[0];
  const redirectTo = useMemo(() => getRedirectTarget(location.state), [location.state]);

  const [name, setName] = useState(demoUser.name);
  const [email, setEmail] = useState(demoUser.email);

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!name.trim() || !email.trim()) {
      toast.error('Lutfen ad ve e-posta alanlarini doldurun.');
      return;
    }

    login({ name, email });
    toast.success('Oturum acildi. Dashboard ekranina yonlendiriliyorsunuz.');
    navigate(redirectTo, { replace: true });
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.18),_transparent_35%),linear-gradient(135deg,_#f8fafc_0%,_#eef2ff_45%,_#e0f2fe_100%)] px-4 py-10">
      <div className="mx-auto flex min-h-[calc(100vh-5rem)] w-full max-w-5xl items-center justify-center">
        <div className="grid w-full gap-8 lg:grid-cols-[1.15fr_0.85fr]">
          <section className="hidden rounded-[32px] border border-white/70 bg-white/55 p-10 shadow-2xl shadow-sky-200/40 backdrop-blur-xl lg:block">
            <div className="mb-8 inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-sky-500 to-indigo-600 text-white shadow-lg shadow-sky-500/25">
              <Calendar className="h-7 w-7" />
            </div>
            <h1 className="max-w-md text-4xl font-semibold leading-tight text-slate-900">
              Toplantilari yonet, odaya gec ve LiveKit deneyimini tek yerden baslat.
            </h1>
            <p className="mt-4 max-w-xl text-base leading-7 text-slate-600">
              `fullfrontend` artik yeni ana giris noktasi. Oturum acip dashboard'a gecebilir,
              yeni toplanti olusturabilir ve dogrudan tam ekran gorusme odasina katilabilirsiniz.
            </p>
            <div className="mt-10 grid gap-4 sm:grid-cols-2">
              <div className="rounded-2xl border border-sky-100 bg-white/80 p-5">
                <p className="text-sm font-semibold text-slate-900">Hizli giris</p>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  Form mock kimlik dogrulamasi kullanir ve kullaniciyi korumali rotalara tasir.
                </p>
              </div>
              <div className="rounded-2xl border border-sky-100 bg-white/80 p-5">
                <p className="text-sm font-semibold text-slate-900">Canli toplanti</p>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  Toplanti detayindan meeting room ekranina gecip lobby ve gorusme arayuzunu kullanin.
                </p>
              </div>
            </div>
          </section>

          <Card className="border-slate-200/80 bg-white/90 shadow-2xl shadow-slate-300/30 backdrop-blur-xl">
            <CardHeader className="space-y-3 pb-2">
              <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-950 text-white">
                <LockKeyhole className="h-6 w-6" />
              </div>
              <div>
                <CardTitle className="text-2xl text-slate-950">Giris Yap</CardTitle>
                <CardDescription className="mt-1 text-sm leading-6 text-slate-600">
                  Basit login akisini tamamlayip dashboard, toplanti olusturma ve meeting room
                  rotalarini aktif hale getirin.
                </CardDescription>
              </div>
            </CardHeader>
            <CardContent className="pt-4">
              <form onSubmit={handleSubmit} className="space-y-5">
                <div className="space-y-2">
                  <Label htmlFor="name">Ad Soyad</Label>
                  <div className="relative">
                    <UserRound className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                    <Input
                      id="name"
                      value={name}
                      onChange={(event) => setName(event.target.value)}
                      className="pl-10"
                      placeholder="Ornek: Ahmet Yilmaz"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="email">E-posta</Label>
                  <div className="relative">
                    <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                    <Input
                      id="email"
                      type="email"
                      value={email}
                      onChange={(event) => setEmail(event.target.value)}
                      className="pl-10"
                      placeholder="ornek@company.com"
                    />
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                  Demo kullanici varsayilan olarak dolduruldu. Dilerseniz farkli bir isim ve e-posta
                  ile de giris yapabilirsiniz.
                </div>

                <Button type="submit" className="h-11 w-full bg-slate-950 text-white hover:bg-slate-800">
                  Dashboard'a Gec
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
