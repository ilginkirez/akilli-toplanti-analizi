import { useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router';
import { Building2, Calendar, LockKeyhole, Mail, UserRound } from 'lucide-react';
import { toast } from 'sonner';

import { useAuth } from '../auth/AuthContext';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';


const DEMO_EMAIL = 'ahmet.yilmaz@company.com';
const DEMO_PASSWORD = 'demo1234';


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
  const { login, register } = useAuth();
  const redirectTo = useMemo(() => getRedirectTarget(location.state), [location.state]);

  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [loginEmail, setLoginEmail] = useState(DEMO_EMAIL);
  const [loginPassword, setLoginPassword] = useState(DEMO_PASSWORD);

  const [registerName, setRegisterName] = useState('');
  const [registerEmail, setRegisterEmail] = useState('');
  const [registerDepartment, setRegisterDepartment] = useState('');
  const [registerPassword, setRegisterPassword] = useState('');
  const [registerPasswordConfirm, setRegisterPasswordConfirm] = useState('');
  const [companyCode, setCompanyCode] = useState('');
  const [companyName, setCompanyName] = useState('');

  const handleLoginSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!loginEmail.trim() || !loginPassword.trim()) {
      toast.error('E-posta ve şifre zorunludur.');
      return;
    }

    setIsSubmitting(true);
    try {
      await login({
        email: loginEmail.trim(),
        password: loginPassword,
      });
      toast.success('Oturum açıldı.');
      navigate(redirectTo, { replace: true });
    } catch (error: any) {
      toast.error('Giriş başarısız', {
        description: error?.message ?? 'Bilgiler doğrulanamadı.',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRegisterSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!registerName.trim() || !registerEmail.trim() || !registerPassword.trim()) {
      toast.error('Ad, e-posta ve şifre zorunludur.');
      return;
    }

    if (registerPassword !== registerPasswordConfirm) {
      toast.error('Şifre tekrar alanı aynı olmalıdır.');
      return;
    }

    setIsSubmitting(true);
    try {
      await register({
        name: registerName.trim(),
        email: registerEmail.trim(),
        password: registerPassword,
        department: registerDepartment.trim() || undefined,
        companyCode: companyCode.trim() || undefined,
        companyName: companyName.trim() || undefined,
      });
      toast.success('Hesap oluşturuldu.');
      navigate(redirectTo, { replace: true });
    } catch (error: any) {
      toast.error('Üyelik oluşturulamadı', {
        description: error?.message ?? 'Kayıt tamamlanamadı.',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(14,165,233,0.18),_transparent_34%),linear-gradient(135deg,_#f8fafc_0%,_#e0f2fe_42%,_#eef2ff_100%)] px-4 py-10">
      <div className="mx-auto flex min-h-[calc(100vh-5rem)] w-full max-w-6xl items-center justify-center">
        <div className="grid w-full gap-8 lg:grid-cols-[1.1fr_0.9fr]">
          <section className="hidden rounded-[32px] border border-white/70 bg-white/60 p-10 shadow-2xl shadow-sky-200/40 backdrop-blur-xl lg:block">
            <div className="mb-8 inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-sky-500 to-indigo-600 text-white shadow-lg shadow-sky-500/25">
              <Calendar className="h-7 w-7" />
            </div>
            <h1 className="max-w-xl text-4xl font-semibold leading-tight text-slate-900">
              Şirket içi çalışanları ve harici misafirleri tek bir toplantı akışında yönetin.
            </h1>
            <p className="mt-4 max-w-xl text-base leading-7 text-slate-600">
              Uygulama artık gerçek SQLite tabanlı kullanıcı kayıt sistemiyle çalışmaktadır.
              Kullanıcılar şirket kodu ile ekip dizinine dahil olabilir, çalışanlar ise ekip
              arkadaşlarını doğrudan seçerek hızlıca toplantı planlayabilir.
            </p>

            <div className="mt-10 grid gap-4 sm:grid-cols-2">
              <div className="rounded-2xl border border-sky-100 bg-white/80 p-5">
                <p className="text-sm font-semibold text-slate-900">Demo Hesap</p>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  E-posta: {DEMO_EMAIL}
                  <br />
                  Şifre: {DEMO_PASSWORD}
                </p>
              </div>
              <div className="rounded-2xl border border-sky-100 bg-white/80 p-5">
                <p className="text-sm font-semibold text-slate-900">Şirket Akışı</p>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  Şirket kodu ile kayıt olan kullanıcılar aynı ekip altında listelenir. Şirket
                  kodu girilmeden oluşturulan hesaplar ise bağımsız kullanıcı olarak tanımlanır.
                </p>
              </div>
            </div>
          </section>

          <Card className="border-slate-200/80 bg-white/90 shadow-2xl shadow-slate-300/30 backdrop-blur-xl">
            <CardHeader className="space-y-4 pb-2">
              <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-950 text-white">
                {mode === 'login' ? <LockKeyhole className="h-6 w-6" /> : <Building2 className="h-6 w-6" />}
              </div>
              <div className="flex rounded-2xl border border-slate-200 bg-slate-50 p-1">
                <button
                  type="button"
                  onClick={() => setMode('login')}
                  className={`flex-1 rounded-xl px-4 py-2 text-sm font-medium transition ${
                    mode === 'login' ? 'bg-white text-slate-950 shadow-sm' : 'text-slate-500'
                  }`}
                >
                  Giriş Yap
                </button>
                <button
                  type="button"
                  onClick={() => setMode('register')}
                  className={`flex-1 rounded-xl px-4 py-2 text-sm font-medium transition ${
                    mode === 'register' ? 'bg-white text-slate-950 shadow-sm' : 'text-slate-500'
                  }`}
                >
                  Üye Ol
                </button>
              </div>
              <div>
                <CardTitle className="text-2xl text-slate-950">
                  {mode === 'login' ? 'Hesabınıza Giriş Yapın' : 'Yeni Hesap Oluşturun'}
                </CardTitle>
                <CardDescription className="mt-1 text-sm leading-6 text-slate-600">
                  {mode === 'login'
                    ? 'Gerçek kullanıcı oturumu ile panel ve toplantı ekranlarına erişin.'
                    : 'İsteğe bağlı şirket kodu ile ekip dizinine katılın veya bağımsız hesap oluşturun.'}
                </CardDescription>
              </div>
            </CardHeader>

            <CardContent className="pt-4">
              {mode === 'login' ? (
                <form onSubmit={handleLoginSubmit} className="space-y-5">
                  <div className="space-y-2">
                    <Label htmlFor="login-email">E-posta</Label>
                    <div className="relative">
                      <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                      <Input
                        id="login-email"
                        type="email"
                        value={loginEmail}
                        onChange={(event) => setLoginEmail(event.target.value)}
                        className="pl-10"
                        placeholder="ornek@company.com"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="login-password">Şifre</Label>
                    <div className="relative">
                      <LockKeyhole className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                      <Input
                        id="login-password"
                        type="password"
                        value={loginPassword}
                        onChange={(event) => setLoginPassword(event.target.value)}
                        className="pl-10"
                        placeholder="En az 8 karakter"
                      />
                    </div>
                  </div>

                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                    Demo hesap veritabanına hazır olarak eklenmiştir. İsterseniz kendi hesabınızla
                    da giriş yapabilirsiniz.
                  </div>

                  <Button
                    type="submit"
                    disabled={isSubmitting}
                    className="h-11 w-full bg-slate-950 text-white hover:bg-slate-800"
                  >
                    {isSubmitting ? 'Giriş yapılıyor...' : "Panel'e Geç"}
                  </Button>
                </form>
              ) : (
                <form onSubmit={handleRegisterSubmit} className="space-y-5">
                  <div className="space-y-2">
                    <Label htmlFor="register-name">Ad Soyad</Label>
                    <div className="relative">
                      <UserRound className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                      <Input
                        id="register-name"
                        value={registerName}
                        onChange={(event) => setRegisterName(event.target.value)}
                        className="pl-10"
                        placeholder="Örnek: Ahmet Yılmaz"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="register-email">E-posta</Label>
                    <div className="relative">
                      <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                      <Input
                        id="register-email"
                        type="email"
                        value={registerEmail}
                        onChange={(event) => setRegisterEmail(event.target.value)}
                        className="pl-10"
                        placeholder="ornek@company.com"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="register-department">Departman</Label>
                    <Input
                      id="register-department"
                      value={registerDepartment}
                      onChange={(event) => setRegisterDepartment(event.target.value)}
                      placeholder="Örnek: Ürün Geliştirme"
                    />
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="register-password">Şifre</Label>
                      <Input
                        id="register-password"
                        type="password"
                        value={registerPassword}
                        onChange={(event) => setRegisterPassword(event.target.value)}
                        placeholder="En az 8 karakter"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="register-password-confirm">Şifre Tekrar</Label>
                      <Input
                        id="register-password-confirm"
                        type="password"
                        value={registerPasswordConfirm}
                        onChange={(event) => setRegisterPasswordConfirm(event.target.value)}
                        placeholder="Şifreyi tekrar girin"
                      />
                    </div>
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="company-code">Şirket Kodu</Label>
                      <Input
                        id="company-code"
                        value={companyCode}
                        onChange={(event) => setCompanyCode(event.target.value)}
                        placeholder="Opsiyonel: COMPANY"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="company-name">Şirket Adı</Label>
                      <Input
                        id="company-name"
                        value={companyName}
                        onChange={(event) => setCompanyName(event.target.value)}
                        placeholder="Yeni bir kod kullanıyorsanız doldurun"
                      />
                    </div>
                  </div>

                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                    Şirket kodu girerseniz aynı ekipteki çalışanlar toplantı ekranında
                    seçilebilir. Kod boş bırakılırsa hesabınız bağımsız olarak açılır.
                  </div>

                  <Button
                    type="submit"
                    disabled={isSubmitting}
                    className="h-11 w-full bg-slate-950 text-white hover:bg-slate-800"
                  >
                    {isSubmitting ? 'Hesap oluşturuluyor...' : 'Hesap Oluştur'}
                  </Button>
                </form>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
