import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router';
import { ArrowLeft, Building2, Calendar as CalendarIcon, Clock, Mail, Plus, Search, Sparkles, Users, X } from 'lucide-react';
import { toast } from 'sonner';

import { listCompanyMembers } from '../auth/api';
import { useAuth } from '../auth/AuthContext';
import { Avatar, AvatarFallback, AvatarImage } from '../components/ui/avatar';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { useMeetings } from '../meetings/MeetingsContext';
import type { CreateMeetingParticipantInput } from '../meetings/api';
import type { User } from '../types';
import { getInitials } from '../utils/helpers';


type GuestDraft = {
  name: string;
  email: string;
  department: string;
};


export function CreateMeeting() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { createMeeting } = useMeetings();

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [date, setDate] = useState('');
  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime] = useState('');
  const [companyMembers, setCompanyMembers] = useState<User[]>([]);
  const [membersLoading, setMembersLoading] = useState(false);
  const [memberSearch, setMemberSearch] = useState('');
  const [selectedMemberIds, setSelectedMemberIds] = useState<string[]>([]);
  const [externalGuests, setExternalGuests] = useState<CreateMeetingParticipantInput[]>([]);
  const [guestDraft, setGuestDraft] = useState<GuestDraft>({
    name: '',
    email: '',
    department: '',
  });
  const [agendaItems, setAgendaItems] = useState<Array<{ id: string; title: string; duration: number }>>([]);
  const [newAgendaItem, setNewAgendaItem] = useState('');
  const [newAgendaDuration, setNewAgendaDuration] = useState('30');

  useEffect(() => {
    if (!user?.companyId) {
      setCompanyMembers([]);
      return;
    }

    let isMounted = true;
    setMembersLoading(true);
    void listCompanyMembers()
      .then((members) => {
        if (!isMounted) {
          return;
        }
        setCompanyMembers(members);
      })
      .catch((error: any) => {
        if (!isMounted) {
          return;
        }
        toast.error('Sirket kullanicilari yuklenemedi', {
          description: error?.message ?? 'Kullanici dizini okunamadi.',
        });
      })
      .finally(() => {
        if (isMounted) {
          setMembersLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [user?.companyId]);

  const selectedMembers = useMemo(
    () => companyMembers.filter((member) => selectedMemberIds.includes(member.id)),
    [companyMembers, selectedMemberIds],
  );

  const availableMembers = useMemo(() => {
    const query = memberSearch.trim().toLowerCase();
    return companyMembers.filter((member) => {
      if (user?.id === member.id) {
        return false;
      }
      if (selectedMemberIds.includes(member.id)) {
        return false;
      }
      if (!query) {
        return true;
      }
      return (
        member.name.toLowerCase().includes(query) ||
        member.email.toLowerCase().includes(query) ||
        member.department.toLowerCase().includes(query)
      );
    });
  }, [companyMembers, memberSearch, selectedMemberIds, user?.id]);

  const handleAddMember = (memberId: string) => {
    setSelectedMemberIds((current) => (current.includes(memberId) ? current : [...current, memberId]));
  };

  const handleRemoveMember = (memberId: string) => {
    setSelectedMemberIds((current) => current.filter((id) => id !== memberId));
  };

  const handleAddGuest = () => {
    if (!guestDraft.name.trim() || !guestDraft.email.trim()) {
      toast.error('Harici katilimci icin ad ve e-posta gerekli.');
      return;
    }

    const nextGuest: CreateMeetingParticipantInput = {
      id: `guest-${Date.now()}`,
      participantType: 'external_guest',
      name: guestDraft.name.trim(),
      email: guestDraft.email.trim(),
      department: guestDraft.department.trim() || 'Harici Katilimci',
      role: 'member',
    };

    setExternalGuests((current) => {
      const exists = current.some((item) => item.email.toLowerCase() === nextGuest.email.toLowerCase());
      if (exists) {
        toast.error('Bu e-posta ile harici katilimci zaten eklendi.');
        return current;
      }
      return [...current, nextGuest];
    });

    setGuestDraft({
      name: '',
      email: '',
      department: '',
    });
  };

  const handleRemoveGuest = (guestId: string) => {
    setExternalGuests((current) => current.filter((guest) => guest.id !== guestId));
  };

  const handleAddAgendaItem = () => {
    if (!newAgendaItem.trim()) {
      return;
    }

    setAgendaItems((current) => [
      ...current,
      {
        id: `agenda-${Date.now()}`,
        title: newAgendaItem.trim(),
        duration: parseInt(newAgendaDuration, 10) || 30,
      },
    ]);
    setNewAgendaItem('');
    setNewAgendaDuration('30');
  };

  const handleRemoveAgendaItem = (id: string) => {
    setAgendaItems((current) => current.filter((item) => item.id !== id));
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!user) {
      toast.error('Aktif kullanici bulunamadi. Lutfen tekrar giris yapin.');
      return;
    }

    if (!title || !date || !startTime || !endTime) {
      toast.error('Lutfen tum zorunlu alanlari doldurun');
      return;
    }

    if (selectedMemberIds.length + externalGuests.length === 0) {
      toast.error('Lutfen en az bir katilimci secin veya harici misafir ekleyin');
      return;
    }

    const startDateTime = new Date(`${date}T${startTime}:00`);
    const endDateTime = new Date(`${date}T${endTime}:00`);

    if (Number.isNaN(startDateTime.getTime()) || Number.isNaN(endDateTime.getTime())) {
      toast.error('Toplanti tarihini ve saatlerini gecerli girin');
      return;
    }

    if (endDateTime <= startDateTime) {
      toast.error('Bitis saati baslangic saatinden sonra olmali');
      return;
    }

    const internalParticipants: CreateMeetingParticipantInput[] = selectedMembers.map((member) => ({
      id: member.id,
      userId: member.id,
      participantType: 'internal_user',
      name: member.name,
      email: member.email,
      avatar: member.avatar,
      role: member.role,
      department: member.department,
    }));

    const participants = Array.from(
      new Map(
        [...internalParticipants, ...externalGuests].map((participant) => [
          participant.email.toLowerCase(),
          participant,
        ]),
      ).values(),
    );

    try {
      const meeting = await createMeeting({
        title,
        description,
        startTime: startDateTime,
        endTime: endDateTime,
        participants,
        agenda: agendaItems.map((item) => ({
          title: item.title,
          duration: item.duration,
        })),
        organizer: user,
      });

      toast.success('Toplanti basariyla olusturuldu', {
        description: 'Detay sayfasina yonlendiriliyorsunuz.',
      });

      navigate(`/meetings/${meeting.id}`);
    } catch (error: any) {
      toast.error('Toplanti olusturulamadi', {
        description: error?.message ?? 'Backend istegi basarisiz oldu.',
      });
    }
  };

  return (
    <div className="max-w-6xl space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/meetings')} className="rounded-full">
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <h1 className="bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-3xl font-bold text-transparent dark:from-white dark:to-gray-300">
            Yeni Toplanti Olustur
          </h1>
          <p className="mt-1 text-gray-600 dark:text-gray-400">
            Sirket icinden calisan ekle, gerekirse harici misafir davet et ve toplantiyi gercek
            veriyle planla.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <Card className="border-gray-200 dark:border-gray-800">
          <CardHeader>
            <CardTitle>Temel Bilgiler</CardTitle>
            <CardDescription>Baslik, aciklama ve toplanti amaci</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="title">Toplanti Basligi *</Label>
              <Input
                id="title"
                placeholder="Ornek: Q2 Strateji Toplantisi"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Aciklama</Label>
              <Textarea
                id="description"
                placeholder="Toplantinin amacini ve konularini yazin..."
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                rows={4}
              />
            </div>
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-800">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CalendarIcon className="h-5 w-5" />
              Tarih ve Saat
            </CardTitle>
            <CardDescription>Baslangic ve bitis zamanini belirleyin</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="date">Tarih *</Label>
              <Input id="date" type="date" value={date} onChange={(event) => setDate(event.target.value)} required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="startTime">Baslangic Saati *</Label>
              <Input
                id="startTime"
                type="time"
                value={startTime}
                onChange={(event) => setStartTime(event.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="endTime">Bitis Saati *</Label>
              <Input
                id="endTime"
                type="time"
                value={endTime}
                onChange={(event) => setEndTime(event.target.value)}
                required
              />
            </div>
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-800">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Building2 className="h-5 w-5" />
              Sirket Ici Katilimcilar
            </CardTitle>
            <CardDescription>
              {user?.companyName || user?.companyCode
                ? `${user.companyName ?? user.companyCode} ekibinden kullanicilar`
                : 'Bu hesap bir sirket dizinine bagli degil'}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {selectedMembers.length > 0 && (
              <div className="space-y-2">
                <Label>Secilen Calisanlar</Label>
                <div className="flex flex-wrap gap-2">
                  {selectedMembers.map((member) => (
                    <Badge key={member.id} variant="secondary" className="flex items-center gap-2 py-1 pl-2 pr-1">
                      <Avatar className="h-5 w-5">
                        <AvatarImage src={member.avatar} />
                        <AvatarFallback className="text-xs">{getInitials(member.name)}</AvatarFallback>
                      </Avatar>
                      <span>{member.name}</span>
                      <button
                        type="button"
                        onClick={() => handleRemoveMember(member.id)}
                        className="ml-1 rounded-full p-0.5 hover:bg-gray-200 dark:hover:bg-gray-700"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {!user?.companyId ? (
              <div className="rounded-2xl border border-dashed border-gray-300 bg-gray-50 p-4 text-sm text-gray-600">
                Bu kullanici bir sirket koduna bagli degil. Sirket ici kisi secmek icin uye olurken
                veya profilinde sirket kodu kullanilmasi gerekir.
              </div>
            ) : (
              <>
                <div className="space-y-2">
                  <Label htmlFor="member-search">Sirket Icisinde Ara</Label>
                  <div className="relative">
                    <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                    <Input
                      id="member-search"
                      value={memberSearch}
                      onChange={(event) => setMemberSearch(event.target.value)}
                      className="pl-10"
                      placeholder="Ad, e-posta veya departman ara"
                    />
                  </div>
                </div>

                {membersLoading ? (
                  <div className="rounded-2xl border border-dashed border-gray-300 bg-gray-50 p-4 text-sm text-gray-600">
                    Sirket dizini yukleniyor...
                  </div>
                ) : availableMembers.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-gray-300 bg-gray-50 p-4 text-sm text-gray-600">
                    Secilebilir baska sirket kullanicisi bulunamadi.
                  </div>
                ) : (
                  <div className="grid gap-3 md:grid-cols-2">
                    {availableMembers.map((member) => (
                      <button
                        key={member.id}
                        type="button"
                        onClick={() => handleAddMember(member.id)}
                        className="flex items-center gap-3 rounded-lg border border-gray-200 p-3 text-left transition-colors hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-900"
                      >
                        <Avatar className="h-10 w-10">
                          <AvatarImage src={member.avatar} />
                          <AvatarFallback>{getInitials(member.name)}</AvatarFallback>
                        </Avatar>
                        <div className="min-w-0 flex-1">
                          <h4 className="text-sm font-semibold">{member.name}</h4>
                          <p className="text-xs text-gray-600 dark:text-gray-400">{member.department}</p>
                          <p className="truncate text-xs text-gray-500">{member.email}</p>
                        </div>
                        <Plus className="h-4 w-4 text-gray-400" />
                      </button>
                    ))}
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-800">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              Harici Katilimcilar
            </CardTitle>
            <CardDescription>Musteri, aday, partner veya sirket disi konuklari ekleyin</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {externalGuests.length > 0 && (
              <div className="space-y-2">
                <Label>Eklenen Harici Katilimcilar</Label>
                <div className="space-y-2">
                  {externalGuests.map((guest) => (
                    <div
                      key={guest.id}
                      className="flex items-center justify-between rounded-xl border border-gray-200 px-4 py-3 dark:border-gray-800"
                    >
                      <div className="min-w-0">
                        <p className="font-medium">{guest.name}</p>
                        <p className="text-sm text-gray-600 dark:text-gray-400">{guest.email}</p>
                        <p className="text-xs text-gray-500">{guest.department}</p>
                      </div>
                      <Button type="button" variant="ghost" size="icon" onClick={() => handleRemoveGuest(guest.id)}>
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="grid gap-3 md:grid-cols-[1fr_1fr_180px_auto]">
              <div className="space-y-2">
                <Label htmlFor="guest-name">Ad Soyad</Label>
                <Input
                  id="guest-name"
                  value={guestDraft.name}
                  onChange={(event) => setGuestDraft((current) => ({ ...current, name: event.target.value }))}
                  placeholder="Ornek: Deniz Kaya"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="guest-email">E-posta</Label>
                <div className="relative">
                  <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                  <Input
                    id="guest-email"
                    type="email"
                    value={guestDraft.email}
                    onChange={(event) => setGuestDraft((current) => ({ ...current, email: event.target.value }))}
                    className="pl-10"
                    placeholder="konuk@example.com"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="guest-department">Etiket</Label>
                <Input
                  id="guest-department"
                  value={guestDraft.department}
                  onChange={(event) => setGuestDraft((current) => ({ ...current, department: event.target.value }))}
                  placeholder="Musteri / Partner"
                />
              </div>
              <div className="flex items-end">
                <Button type="button" variant="outline" onClick={handleAddGuest} className="w-full">
                  <Plus className="mr-2 h-4 w-4" />
                  Ekle
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-800">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5" />
              Gundem
            </CardTitle>
            <CardDescription>Maddeleri ekleyin ve sure verin</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {agendaItems.length > 0 && (
              <div className="space-y-2">
                {agendaItems.map((item, index) => (
                  <div
                    key={item.id}
                    className="flex items-center gap-3 rounded-lg border border-gray-200 p-3 dark:border-gray-800"
                  >
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-100 text-sm font-semibold text-blue-600 dark:bg-blue-900/30 dark:text-blue-400">
                      {index + 1}
                    </div>
                    <div className="flex-1">
                      <h4 className="text-sm font-semibold">{item.title}</h4>
                      <p className="text-xs text-gray-600 dark:text-gray-400">{item.duration} dakika</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleRemoveAgendaItem(item.id)}
                      className="rounded-full p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div className="flex gap-3">
              <div className="flex-1">
                <Input
                  placeholder="Gundem maddesi..."
                  value={newAgendaItem}
                  onChange={(event) => setNewAgendaItem(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') {
                      event.preventDefault();
                      handleAddAgendaItem();
                    }
                  }}
                />
              </div>
              <div className="w-32">
                <Input
                  type="number"
                  placeholder="Dakika"
                  value={newAgendaDuration}
                  onChange={(event) => setNewAgendaDuration(event.target.value)}
                  min="5"
                  step="5"
                />
              </div>
              <Button type="button" variant="outline" onClick={handleAddAgendaItem}>
                <Plus className="h-4 w-4" />
              </Button>
            </div>

            <div className="flex items-start gap-3 rounded-lg border border-sky-200 bg-gradient-to-r from-sky-50 to-indigo-50 p-4 dark:border-sky-900 dark:from-sky-950/20 dark:to-indigo-950/20">
              <Sparkles className="mt-0.5 h-5 w-5 text-sky-600 dark:text-sky-400" />
              <div className="flex-1">
                <h4 className="mb-1 text-sm font-semibold">Toplanti modeli</h4>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Sirket ici kullanicilar veritabanindan secilir, harici katilimcilar ise toplantiya
                  misafir olarak eklenir.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="flex items-center justify-end gap-3">
          <Button type="button" variant="outline" onClick={() => navigate('/meetings')}>
            Iptal
          </Button>
          <Button
            type="submit"
            className="bg-gradient-to-r from-blue-500 to-purple-600 shadow-lg shadow-blue-500/20 hover:from-blue-600 hover:to-purple-700"
          >
            Toplanti Olustur
          </Button>
        </div>
      </form>
    </div>
  );
}
