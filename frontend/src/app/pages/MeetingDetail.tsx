import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import {
  ArrowLeft,
  BarChart3,
  Calendar,
  Camera,
  CheckCircle2,
  Clock,
  MessageSquare,
  Mic,
  Sparkles,
  Target,
  Users,
  Video,
  Volume2,
} from 'lucide-react';
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { Avatar, AvatarFallback, AvatarImage } from '../components/ui/avatar';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Progress } from '../components/ui/progress';
import { Separator } from '../components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { getMeetingAnalysis, mergeMeetingAnalysis } from '../meetings/api';
import { useMeetings } from '../meetings/MeetingsContext';
import type { Meeting } from '../types';
import {
  formatDateTime,
  formatDuration,
  getInitials,
  getMeetingStatusColor,
  getMeetingStatusLabel,
  getScoreColor,
} from '../utils/helpers';

export function MeetingDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { getCachedMeetingById, fetchMeetingById, setMeeting } = useMeetings();
  const [meeting, setLocalMeeting] = useState<Meeting | null>(() => (id ? getCachedMeetingById(id) : null));
  const [isLoading, setIsLoading] = useState(!meeting);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) {
      setError('Toplanti kimligi bulunamadi.');
      setIsLoading(false);
      return;
    }

    let isActive = true;

    async function loadMeeting() {
      setIsLoading(true);
      setError(null);

      const detail = await fetchMeetingById(id);
      if (!isActive) {
        return;
      }
      if (!detail) {
        setLocalMeeting(null);
        setError('Toplanti bulunamadi.');
        setIsLoading(false);
        return;
      }

      let nextMeeting = detail;
      try {
        const analysis = await getMeetingAnalysis(id);
        nextMeeting = mergeMeetingAnalysis(detail, analysis);
      } catch {
        // Analysis ayri bir endpoint oldugu icin detay ekranini analysis olmadan da gosterebiliriz.
      }

      if (!isActive) {
        return;
      }

      setLocalMeeting(nextMeeting);
      setMeeting(nextMeeting);
      setIsLoading(false);
    }

    void loadMeeting();

    return () => {
      isActive = false;
    };
  }, [fetchMeetingById, id, setMeeting]);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <Calendar className="mb-4 h-16 w-16 animate-pulse text-gray-400" />
        <h2 className="mb-2 text-2xl font-bold">Toplanti yukleniyor</h2>
        <p className="text-gray-600 dark:text-gray-400">Gercek toplanti ve analiz verileri getiriliyor.</p>
      </div>
    );
  }

  if (!meeting || error) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <Calendar className="mb-4 h-16 w-16 text-gray-400" />
        <h2 className="mb-2 text-2xl font-bold">Toplanti bulunamadi</h2>
        <p className="mb-4 text-gray-600 dark:text-gray-400">{error ?? 'Aradiginiz toplanti mevcut degil.'}</p>
        <Link to="/meetings">
          <Button>Toplantilara Don</Button>
        </Link>
      </div>
    );
  }

  const { aiSummary, aiAnalytics, timeline } = meeting;
  const hasTimeline = Boolean(timeline && timeline.length > 0);
  const hasAnalytics = Boolean(aiAnalytics && aiAnalytics.speakingDistribution.length > 0);

  const sentimentData = aiAnalytics
    ? [
        { name: 'Pozitif', value: aiAnalytics.sentimentBreakdown.positive, color: '#10b981' },
        { name: 'Notr', value: aiAnalytics.sentimentBreakdown.neutral, color: '#6b7280' },
        { name: 'Negatif', value: aiAnalytics.sentimentBreakdown.negative, color: '#ef4444' },
      ]
    : [];

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/meetings')} className="rounded-full">
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className="flex-1">
          <div className="mb-2 flex items-center gap-3">
            <h1 className="bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-3xl font-bold text-transparent dark:from-white dark:to-gray-300">
              {meeting.title}
            </h1>
            <Badge className={getMeetingStatusColor(meeting.status)}>{getMeetingStatusLabel(meeting.status)}</Badge>
          </div>
          {meeting.description && <p className="text-gray-600 dark:text-gray-400">{meeting.description}</p>}
        </div>
        {meeting.status !== 'completed' && meeting.status !== 'cancelled' && (
          <Button
            asChild
            className="bg-gradient-to-r from-green-500 to-emerald-600 shadow-lg shadow-green-500/20 hover:from-green-600 hover:to-emerald-700"
          >
            <Link to={`/meeting-room/${meeting.id}`}>
              <Video className="mr-2 h-4 w-4" />
              Toplantiya Katil
            </Link>
          </Button>
        )}
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="border-gray-200 dark:border-gray-800">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 dark:bg-blue-900/30">
                <Calendar className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Tarih & Saat</p>
                <p className="font-semibold">{formatDateTime(meeting.startTime)}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-800">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-100 dark:bg-purple-900/30">
                <Clock className="h-5 w-5 text-purple-600 dark:text-purple-400" />
              </div>
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Sure</p>
                <p className="font-semibold">
                  {Math.round((meeting.endTime.getTime() - meeting.startTime.getTime()) / 60000)} dk
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-800">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-100 dark:bg-green-900/30">
                <Users className="h-5 w-5 text-green-600 dark:text-green-400" />
              </div>
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Katilimcilar</p>
                <p className="font-semibold">{meeting.participants.length} kisi</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-800">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-orange-100 dark:bg-orange-900/30">
                <Target className="h-5 w-5 text-orange-600 dark:text-orange-400" />
              </div>
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Analiz Durumu</p>
                <p className="font-semibold">{meeting.analysis?.status ?? 'pending'}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="grid w-full max-w-3xl grid-cols-4">
          <TabsTrigger value="overview">
            <MessageSquare className="mr-2 h-4 w-4" />
            Genel Bakis
          </TabsTrigger>
          <TabsTrigger value="participants">
            <Users className="mr-2 h-4 w-4" />
            Katilimcilar
          </TabsTrigger>
          <TabsTrigger value="timeline" disabled={!hasTimeline}>
            <MessageSquare className="mr-2 h-4 w-4" />
            Konusma Cizelgesi
          </TabsTrigger>
          <TabsTrigger value="analytics" disabled={!hasAnalytics}>
            <BarChart3 className="mr-2 h-4 w-4" />
            Analitik
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-6 space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            <Card className="border-gray-200 dark:border-gray-800">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-yellow-500" />
                  Gercek Analiz Ozeti
                </CardTitle>
                <CardDescription>Backend'in urettigi mevcut analiz durumu</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="rounded-lg border border-gray-200 p-4 dark:border-gray-800">
                  <p className="text-sm text-gray-600 dark:text-gray-400">Kayit Durumu</p>
                  <p className="mt-1 text-lg font-semibold">{meeting.recording?.status ?? 'pending'}</p>
                </div>
                <div className="rounded-lg border border-gray-200 p-4 dark:border-gray-800">
                  <p className="text-sm text-gray-600 dark:text-gray-400">Konusma Analizi</p>
                  <p className="mt-1 text-lg font-semibold">{meeting.analysis?.status ?? 'pending'}</p>
                  <p className="mt-1 text-xs text-gray-500">
                    Segment: {meeting.analysis?.segmentCount ?? 0} | Ozet: {meeting.analysis?.summaryCount ?? 0}
                  </p>
                </div>
                {!aiSummary && (
                  <div className="rounded-lg border border-dashed border-gray-300 p-4 text-sm text-gray-600 dark:border-gray-700 dark:text-gray-400">
                    Bu fazda yalnizca backend'in gercekten urettigi konusma ve kayit analizi gosteriliyor. LLM tabanli
                    ozet ve karar cikarma henuz bagli degil.
                  </div>
                )}
              </CardContent>
            </Card>

            {aiSummary ? (
              <Card className="border-gray-200 dark:border-gray-800">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <CheckCircle2 className="h-5 w-5 text-green-500" />
                    AI Ozeti
                  </CardTitle>
                  <CardDescription>Mevcut ozet alani</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <p className="text-sm text-gray-600 dark:text-gray-400">{aiSummary.executiveSummary}</p>
                  <Separator />
                  <div className="flex flex-wrap gap-2">
                    {aiSummary.topics.map((topic, idx) => (
                      <Badge key={idx} variant="outline">
                        {topic}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ) : (
              <Card className="border-gray-200 dark:border-gray-800">
                <CardHeader>
                  <CardTitle>Ozet Yok</CardTitle>
                  <CardDescription>Mock yerine gercek veri durumu</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Henuz executive summary, karar maddeleri veya action item uretilmedi.
                  </p>
                </CardContent>
              </Card>
            )}
          </div>

          <Card className="border-gray-200 dark:border-gray-800">
            <CardHeader>
              <CardTitle>Gundem</CardTitle>
              <CardDescription>Toplanti gundem maddeleri</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {meeting.agenda.map((item, idx) => (
                  <div key={item.id} className="flex items-center gap-3 rounded-lg border border-gray-200 p-3 dark:border-gray-800">
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-100 text-sm font-semibold text-blue-600 dark:bg-blue-900/30 dark:text-blue-400">
                      {idx + 1}
                    </div>
                    <div className="flex-1">
                      <h4 className="text-sm font-semibold">{item.title}</h4>
                      <p className="text-xs text-gray-600 dark:text-gray-400">Sure: {item.duration} dakika</p>
                    </div>
                    {item.completed && <CheckCircle2 className="h-5 w-5 text-green-500" />}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="participants" className="mt-6 space-y-6">
          <Card className="border-gray-200 dark:border-gray-800">
            <CardHeader>
              <CardTitle>Katilimcilar</CardTitle>
              <CardDescription>Toplanti katilimci listesi ve gercek runtime bilgileri</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {meeting.participants.map((participant) => (
                  <div
                    key={`${participant.user.email}-${participant.user.id}`}
                    className="flex items-center gap-4 rounded-lg border border-gray-200 p-4 dark:border-gray-800"
                  >
                    <Avatar className="h-12 w-12">
                      <AvatarImage src={participant.user.avatar} />
                      <AvatarFallback>{getInitials(participant.user.name)}</AvatarFallback>
                    </Avatar>
                    <div className="flex-1">
                      <h4 className="font-semibold">{participant.user.name}</h4>
                      <p className="text-sm text-gray-600 dark:text-gray-400">{participant.user.department}</p>
                      {(participant.joinedAt || participant.speakingTime) && (
                        <div className="mt-2 flex flex-wrap items-center gap-3">
                          {participant.joinedAt && (
                            <div className="text-xs text-gray-600 dark:text-gray-400">
                              Katildi: {formatDateTime(participant.joinedAt)}
                            </div>
                          )}
                          {participant.speakingTime !== undefined && (
                            <div className="flex items-center gap-1 text-xs text-gray-600 dark:text-gray-400">
                              <Volume2 className="h-3 w-3" />
                              {formatDuration(Math.round(participant.speakingTime))}
                            </div>
                          )}
                          {participant.cameraOnTime !== undefined && (
                            <div className="flex items-center gap-1 text-xs text-gray-600 dark:text-gray-400">
                              <Camera className="h-3 w-3" />
                              {formatDuration(Math.round(participant.cameraOnTime))}
                            </div>
                          )}
                          {participant.micOnTime !== undefined && (
                            <div className="flex items-center gap-1 text-xs text-gray-600 dark:text-gray-400">
                              <Mic className="h-3 w-3" />
                              {formatDuration(Math.round(participant.micOnTime))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                    <Badge
                      variant={
                        participant.status === 'accepted'
                          ? 'default'
                          : participant.status === 'pending'
                            ? 'secondary'
                            : 'destructive'
                      }
                    >
                      {participant.status === 'accepted'
                        ? 'Katilacak'
                        : participant.status === 'pending'
                          ? 'Bekliyor'
                          : 'Reddetti'}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="timeline" className="mt-6 space-y-6">
          <Card className="border-gray-200 dark:border-gray-800">
            <CardHeader>
              <CardTitle>Konusma Zaman Cizelgesi</CardTitle>
              <CardDescription>Speech analysis servisinden gelen gercek konusma segmentleri</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {timeline?.map((segment) => (
                  <div key={segment.id} className="rounded-lg border border-gray-200 p-4 dark:border-gray-800">
                    <div className="mb-2 flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">{segment.type === 'overlap' ? 'Overlap' : 'Single Speaker'}</Badge>
                        <span className="text-sm font-semibold">
                          {segment.participants.map((participant) => participant.displayName).join(', ')}
                        </span>
                      </div>
                      <span className="text-xs text-gray-500">
                        {formatDuration(Math.floor(segment.startTime))} - {formatDuration(Math.floor(segment.endTime))}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Sure: {segment.duration.toFixed(2)} sn
                      {segment.startAt ? ` | Baslangic: ${formatDateTime(segment.startAt)}` : ''}
                    </p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="analytics" className="mt-6 space-y-6">
          {aiAnalytics && (
            <div className="grid gap-6 lg:grid-cols-2">
              <Card className="border-gray-200 dark:border-gray-800">
                <CardHeader>
                  <CardTitle>Konusma Dagilimi</CardTitle>
                  <CardDescription>Katilimcilarin gercek konusma sureleri</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={aiAnalytics.speakingDistribution}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="userName" angle={-35} textAnchor="end" height={70} />
                        <YAxis />
                        <Tooltip />
                        <Bar dataKey="percentage" fill="#3b82f6" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>

              <Card className="border-gray-200 dark:border-gray-800">
                <CardHeader>
                  <CardTitle>Duygu Dagilimi</CardTitle>
                  <CardDescription>Bu fazda sentiment alanlari bossa sifir gorunur</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={sentimentData} cx="50%" cy="50%" innerRadius={60} outerRadius={90} dataKey="value">
                          {sentimentData.map((entry, index) => (
                            <Cell key={`sentiment-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <Tooltip />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>

              <Card className="border-gray-200 dark:border-gray-800 lg:col-span-2">
                <CardHeader>
                  <CardTitle>Katilim Metrikleri</CardTitle>
                  <CardDescription>Gercek attendance ve konusma dagilimi verileri</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-6 md:grid-cols-3">
                    <div>
                      <p className="mb-2 text-sm text-gray-600 dark:text-gray-400">Ortalama Katilim</p>
                      <div className="flex items-center gap-3">
                        <Progress value={aiAnalytics.averageAttendance} className="h-3" />
                        <span className="text-lg font-bold">{aiAnalytics.averageAttendance}%</span>
                      </div>
                    </div>
                    <div>
                      <p className="mb-2 text-sm text-gray-600 dark:text-gray-400">Etkilesim Skoru</p>
                      <div className="flex items-center gap-3">
                        <Progress value={aiAnalytics.engagementScore} className="h-3" />
                        <span className={`text-lg font-bold ${getScoreColor(aiAnalytics.engagementScore)}`}>
                          {aiAnalytics.engagementScore}
                        </span>
                      </div>
                    </div>
                    <div>
                      <p className="mb-2 text-sm text-gray-600 dark:text-gray-400">Toplam Katilimci</p>
                      <div className="flex items-center gap-3">
                        <Users className="h-6 w-6 text-blue-500" />
                        <span className="text-lg font-bold">{aiAnalytics.totalParticipants}</span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
