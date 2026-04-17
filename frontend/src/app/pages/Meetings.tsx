import { useState } from 'react';
import { Link } from 'react-router';
import { Calendar, Clock, Filter, Plus, Search, Users } from 'lucide-react';

import { Avatar, AvatarFallback, AvatarImage } from '../components/ui/avatar';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { useMeetings } from '../meetings/MeetingsContext';
import type { Meeting } from '../types';
import {
  getInitials,
  getMeetingStatusColor,
  getMeetingStatusLabel,
  getRelativeTime,
} from '../utils/helpers';

export function Meetings() {
  const [searchQuery, setSearchQuery] = useState('');
  const { meetings, isLoading, error } = useMeetings();

  const upcomingMeetings = meetings
    .filter((meeting) => meeting.status === 'upcoming')
    .sort((left, right) => left.startTime.getTime() - right.startTime.getTime());

  const completedMeetings = meetings
    .filter((meeting) => meeting.status === 'completed')
    .sort((left, right) => right.startTime.getTime() - left.startTime.getTime());

  const allMeetings = [...meetings].sort((left, right) => right.startTime.getTime() - left.startTime.getTime());

  const filterMeetings = (items: Meeting[]) => {
    if (!searchQuery) {
      return items;
    }

    return items.filter(
      (meeting) =>
        meeting.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        meeting.description?.toLowerCase().includes(searchQuery.toLowerCase()),
    );
  };

  const MeetingCard = ({ meeting }: { meeting: Meeting }) => (
    <Link to={`/meetings/${meeting.id}`}>
      <Card className="cursor-pointer border-gray-200 transition-all duration-200 hover:border-blue-300 hover:shadow-lg dark:border-gray-800 dark:hover:border-blue-700">
        <CardContent className="p-6">
          <div className="flex items-start gap-4">
            <div className="flex h-14 w-14 flex-shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 shadow-lg shadow-blue-500/20">
              <Calendar className="h-7 w-7 text-white" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="mb-2 flex items-start justify-between gap-2">
                <h3 className="text-lg font-semibold">{meeting.title}</h3>
                <Badge className={getMeetingStatusColor(meeting.status)}>
                  {getMeetingStatusLabel(meeting.status)}
                </Badge>
              </div>

              {meeting.description && (
                <p className="mb-3 line-clamp-2 text-sm text-gray-600 dark:text-gray-400">
                  {meeting.description}
                </p>
              )}

              <div className="mb-3 flex flex-wrap items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
                <span className="flex items-center gap-1.5">
                  <Clock className="h-4 w-4" />
                  {getRelativeTime(meeting.startTime)}
                </span>
                <span className="flex items-center gap-1.5">
                  <Users className="h-4 w-4" />
                  {meeting.participants.length} katılımcı
                </span>
              </div>

              <div className="flex items-center gap-2">
                {meeting.participants.slice(0, 5).map((participant) => (
                  <Avatar key={participant.user.id} className="h-8 w-8 border-2 border-white dark:border-gray-900">
                    <AvatarImage src={participant.user.avatar} />
                    <AvatarFallback className="text-xs">{getInitials(participant.user.name)}</AvatarFallback>
                  </Avatar>
                ))}
                {meeting.participants.length > 5 && (
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-200 text-xs font-medium dark:bg-gray-800">
                    +{meeting.participants.length - 5}
                  </div>
                )}
              </div>

              {meeting.agenda.length > 0 && (
                <div className="mt-3 border-t border-gray-200 pt-3 dark:border-gray-800">
                  <p className="mb-1 text-xs text-gray-500 dark:text-gray-400">Gündem</p>
                  <div className="flex flex-wrap gap-2">
                    {meeting.agenda.slice(0, 3).map((item) => (
                      <Badge key={item.id} variant="outline" className="text-xs">
                        {item.title}
                      </Badge>
                    ))}
                    {meeting.agenda.length > 3 && (
                      <Badge variant="outline" className="text-xs">
                        +{meeting.agenda.length - 3} daha
                      </Badge>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-3xl font-bold text-transparent dark:from-white dark:to-gray-300">
            Toplantılar
          </h1>
          <p className="mt-1 text-gray-600 dark:text-gray-400">
            Tüm toplantılarınızı yönetin, inceleyin ve odaya geçin.
          </p>
        </div>
        <Link to="/meetings/new">
          <Button className="bg-gradient-to-r from-blue-500 to-purple-600 shadow-lg shadow-blue-500/20 hover:from-blue-600 hover:to-purple-700">
            <Plus className="mr-2 h-4 w-4" />
            Yeni Toplantı
          </Button>
        </Link>
      </div>

      <Card className="border-gray-200 dark:border-gray-800">
        <CardContent className="p-4">
          <div className="flex gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <Input
                type="search"
                placeholder="Toplantı ara..."
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                className="pl-10"
              />
            </div>
            <Button variant="outline">
              <Filter className="mr-2 h-4 w-4" />
              Filtrele
            </Button>
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="upcoming" className="w-full">
        <TabsList className="grid w-full max-w-md grid-cols-3">
          <TabsTrigger value="upcoming">Yaklaşan ({upcomingMeetings.length})</TabsTrigger>
          <TabsTrigger value="completed">Tamamlanan ({completedMeetings.length})</TabsTrigger>
          <TabsTrigger value="all">Tümü ({allMeetings.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="upcoming" className="mt-6 space-y-4">
          {isLoading ? (
            <Card className="border-gray-200 dark:border-gray-800">
              <CardContent className="flex flex-col items-center justify-center py-16 text-center">
                <Calendar className="mb-4 h-16 w-16 animate-pulse text-gray-400" />
                <h3 className="mb-2 text-lg font-semibold">Toplantilar yukleniyor</h3>
                <p className="text-gray-600 dark:text-gray-400">Gercek toplanti verileri getiriliyor.</p>
              </CardContent>
            </Card>
          ) : error ? (
            <Card className="border-gray-200 dark:border-gray-800">
              <CardContent className="flex flex-col items-center justify-center py-16 text-center">
                <Calendar className="mb-4 h-16 w-16 text-gray-400" />
                <h3 className="mb-2 text-lg font-semibold">Toplantilar yuklenemedi</h3>
                <p className="text-gray-600 dark:text-gray-400">{error}</p>
              </CardContent>
            </Card>
          ) : filterMeetings(upcomingMeetings).length === 0 ? (
            <Card className="border-gray-200 dark:border-gray-800">
              <CardContent className="flex flex-col items-center justify-center py-16 text-center">
                <Calendar className="mb-4 h-16 w-16 text-gray-400" />
                <h3 className="mb-2 text-lg font-semibold">Yaklaşan toplantı yok</h3>
                <p className="mb-4 text-gray-600 dark:text-gray-400">
                  Yeni bir toplantı oluşturarak başlayın.
                </p>
                <Link to="/meetings/new">
                  <Button>
                    <Plus className="mr-2 h-4 w-4" />
                    Yeni Toplantı
                  </Button>
                </Link>
              </CardContent>
            </Card>
          ) : (
            filterMeetings(upcomingMeetings).map((meeting) => <MeetingCard key={meeting.id} meeting={meeting} />)
          )}
        </TabsContent>

        <TabsContent value="completed" className="mt-6 space-y-4">
          {isLoading ? (
            <Card className="border-gray-200 dark:border-gray-800">
              <CardContent className="flex flex-col items-center justify-center py-16 text-center">
                <Calendar className="mb-4 h-16 w-16 animate-pulse text-gray-400" />
                <h3 className="mb-2 text-lg font-semibold">Toplantilar yukleniyor</h3>
              </CardContent>
            </Card>
          ) : filterMeetings(completedMeetings).length === 0 ? (
            <Card className="border-gray-200 dark:border-gray-800">
              <CardContent className="flex flex-col items-center justify-center py-16 text-center">
                <Calendar className="mb-4 h-16 w-16 text-gray-400" />
                <h3 className="mb-2 text-lg font-semibold">Tamamlanan toplantı yok</h3>
                <p className="text-gray-600 dark:text-gray-400">
                  Tamamlanan görüşmeler burada listelenecek.
                </p>
              </CardContent>
            </Card>
          ) : (
            filterMeetings(completedMeetings).map((meeting) => <MeetingCard key={meeting.id} meeting={meeting} />)
          )}
        </TabsContent>

        <TabsContent value="all" className="mt-6 space-y-4">
          {filterMeetings(allMeetings).map((meeting) => (
            <MeetingCard key={meeting.id} meeting={meeting} />
          ))}
        </TabsContent>
      </Tabs>
    </div>
  );
}
