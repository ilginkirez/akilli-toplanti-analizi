import { useState } from 'react';
import { useNavigate } from 'react-router';
import { ArrowLeft, Calendar as CalendarIcon, Clock, Plus, Sparkles, Users, X } from 'lucide-react';
import { toast } from 'sonner';

import { Avatar, AvatarFallback, AvatarImage } from '../components/ui/avatar';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { useAuth } from '../auth/AuthContext';
import { mockUsers } from '../data/mockData';
import { useMeetings } from '../meetings/MeetingsContext';
import { getInitials } from '../utils/helpers';

export function CreateMeeting() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { createMeeting } = useMeetings();

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [date, setDate] = useState('');
  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime] = useState('');
  const [selectedParticipants, setSelectedParticipants] = useState<string[]>([]);
  const [agendaItems, setAgendaItems] = useState<Array<{ id: string; title: string; duration: number }>>([]);
  const [newAgendaItem, setNewAgendaItem] = useState('');
  const [newAgendaDuration, setNewAgendaDuration] = useState('30');

  const handleAddParticipant = (userId: string) => {
    if (!selectedParticipants.includes(userId)) {
      setSelectedParticipants((current) => [...current, userId]);
    }
  };

  const handleRemoveParticipant = (userId: string) => {
    setSelectedParticipants((current) => current.filter((id) => id !== userId));
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

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!title || !date || !startTime || !endTime) {
      toast.error('Lutfen tum zorunlu alanlari doldurun');
      return;
    }

    if (selectedParticipants.length === 0) {
      toast.error('Lutfen en az bir katilimci secin');
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

    const meeting = createMeeting({
      title,
      description,
      startTime: startDateTime,
      endTime: endDateTime,
      participantIds: selectedParticipants,
      agenda: agendaItems.map((item) => ({
        title: item.title,
        duration: item.duration,
      })),
      organizer: user ?? mockUsers[0],
    });

    toast.success('Toplanti basariyla olusturuldu', {
      description: 'Detay sayfasina yonlendiriliyorsunuz.',
    });

    navigate(`/meetings/${meeting.id}`);
  };

  const availableParticipants = mockUsers.filter((candidate) => !selectedParticipants.includes(candidate.id));
  const selectedUsers = mockUsers.filter((candidate) => selectedParticipants.includes(candidate.id));

  return (
    <div className="max-w-5xl space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/meetings')} className="rounded-full">
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <h1 className="bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-3xl font-bold text-transparent dark:from-white dark:to-gray-300">
            Yeni Toplanti Olustur
          </h1>
          <p className="mt-1 text-gray-600 dark:text-gray-400">
            Bilgileri doldurun, katilimcilari secin ve dogrudan yeni toplanti detayina gidin.
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
              <Users className="h-5 w-5" />
              Katilimcilar
            </CardTitle>
            <CardDescription>{selectedParticipants.length} kisi secildi</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {selectedUsers.length > 0 && (
              <div className="space-y-2">
                <Label>Secilen Katilimcilar</Label>
                <div className="flex flex-wrap gap-2">
                  {selectedUsers.map((selectedUser) => (
                    <Badge key={selectedUser.id} variant="secondary" className="flex items-center gap-2 py-1 pl-2 pr-1">
                      <Avatar className="h-5 w-5">
                        <AvatarImage src={selectedUser.avatar} />
                        <AvatarFallback className="text-xs">{getInitials(selectedUser.name)}</AvatarFallback>
                      </Avatar>
                      <span>{selectedUser.name}</span>
                      <button
                        type="button"
                        onClick={() => handleRemoveParticipant(selectedUser.id)}
                        className="ml-1 rounded-full p-0.5 hover:bg-gray-200 dark:hover:bg-gray-700"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            <div className="space-y-2">
              <Label>Kullanilabilir Kisiler</Label>
              <div className="grid gap-2 md:grid-cols-2">
                {availableParticipants.map((participant) => (
                  <button
                    key={participant.id}
                    type="button"
                    onClick={() => handleAddParticipant(participant.id)}
                    className="flex items-center gap-3 rounded-lg border border-gray-200 p-3 text-left transition-colors hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-900"
                  >
                    <Avatar className="h-10 w-10">
                      <AvatarImage src={participant.avatar} />
                      <AvatarFallback>{getInitials(participant.name)}</AvatarFallback>
                    </Avatar>
                    <div className="min-w-0 flex-1">
                      <h4 className="text-sm font-semibold">{participant.name}</h4>
                      <p className="text-xs text-gray-600 dark:text-gray-400">{participant.department}</p>
                    </div>
                    <Plus className="h-4 w-4 text-gray-400" />
                  </button>
                ))}
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

            <div className="flex items-start gap-3 rounded-lg border border-purple-200 bg-gradient-to-r from-purple-50 to-blue-50 p-4 dark:border-purple-900 dark:from-purple-950/20 dark:to-blue-950/20">
              <Sparkles className="mt-0.5 h-5 w-5 text-purple-600 dark:text-purple-400" />
              <div className="flex-1">
                <h4 className="mb-1 text-sm font-semibold">AI Oneri</h4>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Basliga gore otomatik gundem onerileri sonraki adimda eklenebilir.
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
