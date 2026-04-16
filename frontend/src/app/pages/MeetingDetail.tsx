import { useParams, Link, useNavigate } from 'react-router';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '../components/ui/avatar';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Progress } from '../components/ui/progress';
import { Separator } from '../components/ui/separator';
import { 
  Calendar, Clock, Users, ArrowLeft, Sparkles, MessageSquare, 
  TrendingUp, CheckCircle2, Target, BarChart3, Video, Mic, 
  Camera, Volume2
} from 'lucide-react';
import { 
  formatDateTime, getMeetingStatusColor, getMeetingStatusLabel, 
  getInitials, getSentimentColor, getSentimentLabel, formatDuration,
  getTaskStatusColor, getTaskStatusLabel
} from '../utils/helpers';
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import { useMeetings } from '../meetings/MeetingsContext';

export function MeetingDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { getMeetingById } = useMeetings();
  const meeting = id ? getMeetingById(id) : null;

  if (!meeting) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <Calendar className="h-16 w-16 text-gray-400 mb-4" />
        <h2 className="text-2xl font-bold mb-2">Toplantı bulunamadı</h2>
        <p className="text-gray-600 dark:text-gray-400 mb-4">
          Aradığınız toplantı mevcut değil
        </p>
        <Link to="/meetings">
          <Button>Toplantılara Dön</Button>
        </Link>
      </div>
    );
  }

  const { aiSummary, aiAnalytics, transcript } = meeting;

  // Sentiment data for chart
  const sentimentData = aiAnalytics ? [
    { name: 'Pozitif', value: aiAnalytics.sentimentBreakdown.positive, color: '#10b981' },
    { name: 'Nötr', value: aiAnalytics.sentimentBreakdown.neutral, color: '#6b7280' },
    { name: 'Negatif', value: aiAnalytics.sentimentBreakdown.negative, color: '#ef4444' }
  ] : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/meetings')} className="rounded-full">
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-3xl font-bold bg-gradient-to-r from-gray-900 to-gray-700 dark:from-white dark:to-gray-300 bg-clip-text text-transparent">
              {meeting.title}
            </h1>
            <Badge className={getMeetingStatusColor(meeting.status)}>
              {getMeetingStatusLabel(meeting.status)}
            </Badge>
          </div>
          {meeting.description && (
            <p className="text-gray-600 dark:text-gray-400">{meeting.description}</p>
          )}
        </div>
        {meeting.status === 'upcoming' && (
          <Button
            asChild
            className="bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 shadow-lg shadow-green-500/20"
          >
            <Link to={`/meeting-room/${meeting.id}`}>
              <Video className="mr-2 h-4 w-4" />
              Toplantıya Katıl
            </Link>
          </Button>
        )}
      </div>

      {/* Meeting Info */}
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
                <p className="text-sm text-gray-600 dark:text-gray-400">Süre</p>
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
                <p className="text-sm text-gray-600 dark:text-gray-400">Katılımcılar</p>
                <p className="font-semibold">{meeting.participants.length} kişi</p>
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
                <p className="text-sm text-gray-600 dark:text-gray-400">Gündem Maddeleri</p>
                <p className="font-semibold">{meeting.agenda.length} madde</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="grid w-full max-w-2xl grid-cols-4">
          <TabsTrigger value="overview">
            <MessageSquare className="mr-2 h-4 w-4" />
            Genel Bakış
          </TabsTrigger>
          <TabsTrigger value="participants">
            <Users className="mr-2 h-4 w-4" />
            Katılımcılar
          </TabsTrigger>
          <TabsTrigger value="transcript" disabled={!transcript}>
            <MessageSquare className="mr-2 h-4 w-4" />
            Transkript
          </TabsTrigger>
          <TabsTrigger value="analytics" disabled={!aiAnalytics}>
            <BarChart3 className="mr-2 h-4 w-4" />
            Analitik
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6 mt-6">
          <div className="grid gap-6 lg:grid-cols-2">
            {/* AI Summary */}
            {aiSummary && (
              <Card className="border-gray-200 dark:border-gray-800">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Sparkles className="h-5 w-5 text-yellow-500" />
                    AI Özeti
                  </CardTitle>
                  <CardDescription>Yapay zeka tarafından oluşturulan özet</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <h4 className="text-sm font-semibold mb-2">Yönetici Özeti</h4>
                    <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                      {aiSummary.executiveSummary}
                    </p>
                  </div>
                  <Separator />
                  <div>
                    <h4 className="text-sm font-semibold mb-2">Konular</h4>
                    <div className="flex flex-wrap gap-2">
                      {aiSummary.topics.map((topic, idx) => (
                        <Badge key={idx} variant="outline">
                          {topic}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <Separator />
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Duygu Durumu</p>
                      <Badge className={getSentimentColor(aiSummary.sentiment)}>
                        {getSentimentLabel(aiSummary.sentiment)}
                      </Badge>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Gündeme Sadakat</p>
                      <div className="flex items-center gap-2">
                        <Progress value={aiSummary.agendaAdherence} className="h-2" />
                        <span className="text-sm font-semibold">{aiSummary.agendaAdherence}%</span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Key Decisions */}
            {aiSummary && (
              <Card className="border-gray-200 dark:border-gray-800">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <CheckCircle2 className="h-5 w-5 text-green-500" />
                    Önemli Kararlar
                  </CardTitle>
                  <CardDescription>Toplantıda alınan kararlar</CardDescription>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-3">
                    {aiSummary.keyDecisions.map((decision, idx) => (
                      <li key={idx} className="flex items-start gap-3">
                        <CheckCircle2 className="h-5 w-5 mt-0.5 text-green-500 flex-shrink-0" />
                        <span className="text-sm text-gray-600 dark:text-gray-400">{decision}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Action Items */}
          {aiSummary && aiSummary.actionItems.length > 0 && (
            <Card className="border-gray-200 dark:border-gray-800">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Target className="h-5 w-5 text-blue-500" />
                  Görevler (AI Tarafından Oluşturuldu)
                </CardTitle>
                <CardDescription>Toplantıdan çıkarılan aksiyon maddeleri</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {aiSummary.actionItems.map((task) => (
                    <div
                      key={task.id}
                      className="flex items-start gap-4 p-4 rounded-lg border border-gray-200 dark:border-gray-800"
                    >
                      <Avatar className="h-10 w-10">
                        <AvatarImage src={task.assignee.avatar} />
                        <AvatarFallback>{getInitials(task.assignee.name)}</AvatarFallback>
                      </Avatar>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <h4 className="font-semibold text-sm">{task.title}</h4>
                          <Badge className={getTaskStatusColor(task.status)}>
                            {getTaskStatusLabel(task.status)}
                          </Badge>
                        </div>
                        {task.description && (
                          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                            {task.description}
                          </p>
                        )}
                        <div className="flex items-center gap-3 mt-2 text-xs text-gray-600 dark:text-gray-400">
                          <span>Atanan: {task.assignee.name}</span>
                          <span>•</span>
                          <span>Bitiş: {formatDateTime(task.dueDate)}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Agenda */}
          <Card className="border-gray-200 dark:border-gray-800">
            <CardHeader>
              <CardTitle>Gündem</CardTitle>
              <CardDescription>Toplantı gündem maddeleri</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {meeting.agenda.map((item, idx) => (
                  <div key={item.id} className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 dark:border-gray-800">
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900/30 text-sm font-semibold text-blue-600 dark:text-blue-400">
                      {idx + 1}
                    </div>
                    <div className="flex-1">
                      <h4 className="font-semibold text-sm">{item.title}</h4>
                      <p className="text-xs text-gray-600 dark:text-gray-400">Süre: {item.duration} dakika</p>
                    </div>
                    {item.completed && (
                      <CheckCircle2 className="h-5 w-5 text-green-500" />
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Participants Tab */}
        <TabsContent value="participants" className="space-y-6 mt-6">
          <Card className="border-gray-200 dark:border-gray-800">
            <CardHeader>
              <CardTitle>Katılımcılar</CardTitle>
              <CardDescription>Toplantı katılımcı listesi ve durumları</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {meeting.participants.map((participant) => (
                  <div
                    key={participant.user.id}
                    className="flex items-center gap-4 p-4 rounded-lg border border-gray-200 dark:border-gray-800"
                  >
                    <Avatar className="h-12 w-12">
                      <AvatarImage src={participant.user.avatar} />
                      <AvatarFallback>{getInitials(participant.user.name)}</AvatarFallback>
                    </Avatar>
                    <div className="flex-1">
                      <h4 className="font-semibold">{participant.user.name}</h4>
                      <p className="text-sm text-gray-600 dark:text-gray-400">{participant.user.department}</p>
                      {participant.joinedAt && (
                        <div className="flex items-center gap-3 mt-2">
                          {participant.speakingTime && (
                            <div className="flex items-center gap-1 text-xs text-gray-600 dark:text-gray-400">
                              <Volume2 className="h-3 w-3" />
                              {formatDuration(participant.speakingTime)}
                            </div>
                          )}
                          {participant.cameraOnTime && (
                            <div className="flex items-center gap-1 text-xs text-gray-600 dark:text-gray-400">
                              <Camera className="h-3 w-3" />
                              {formatDuration(participant.cameraOnTime)}
                            </div>
                          )}
                          {participant.micOnTime && (
                            <div className="flex items-center gap-1 text-xs text-gray-600 dark:text-gray-400">
                              <Mic className="h-3 w-3" />
                              {formatDuration(participant.micOnTime)}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                    <Badge variant={
                      participant.status === 'accepted' ? 'default' : 
                      participant.status === 'pending' ? 'secondary' : 
                      'destructive'
                    }>
                      {participant.status === 'accepted' ? 'Kabul Etti' :
                       participant.status === 'pending' ? 'Bekliyor' :
                       'Reddetti'}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Transcript Tab */}
        {transcript && (
          <TabsContent value="transcript" className="space-y-6 mt-6">
            <Card className="border-gray-200 dark:border-gray-800">
              <CardHeader>
                <CardTitle>Konuşma Transkripti</CardTitle>
                <CardDescription>AI tarafından oluşturulan otomatik transkript</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {transcript.segments.map((segment) => (
                    <div key={segment.id} className="flex gap-4">
                      <Avatar className="h-10 w-10">
                        <AvatarImage src={segment.speaker.avatar} />
                        <AvatarFallback>{getInitials(segment.speaker.name)}</AvatarFallback>
                      </Avatar>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-semibold text-sm">{segment.speaker.name}</span>
                          <span className="text-xs text-gray-500">
                            {formatDuration(Math.floor(segment.startTime))}
                          </span>
                          {segment.sentiment && (
                            <Badge variant="outline" className={`text-xs ${getSentimentColor(segment.sentiment)}`}>
                              {getSentimentLabel(segment.sentiment)}
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
                          {segment.text}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        )}

        {/* Analytics Tab */}
        {aiAnalytics && (
          <TabsContent value="analytics" className="space-y-6 mt-6">
            <div className="grid gap-6 lg:grid-cols-2">
              {/* Speaking Distribution */}
              <Card className="border-gray-200 dark:border-gray-800">
                <CardHeader>
                  <CardTitle>Konuşma Dağılımı</CardTitle>
                  <CardDescription>Katılımcıların konuşma süreleri</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={aiAnalytics.speakingDistribution}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="userName" angle={-45} textAnchor="end" height={80} />
                        <YAxis />
                        <Tooltip />
                        <Bar dataKey="percentage" fill="#3b82f6" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>

              {/* Sentiment Breakdown */}
              <Card className="border-gray-200 dark:border-gray-800">
                <CardHeader>
                  <CardTitle>Duygu Analizi</CardTitle>
                  <CardDescription>Toplantının genel duygu dağılımı</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={sentimentData}
                          cx="50%"
                          cy="50%"
                          innerRadius={60}
                          outerRadius={90}
                          paddingAngle={5}
                          dataKey="value"
                        >
                          {sentimentData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <Tooltip />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="flex justify-center gap-6 mt-4">
                    {sentimentData.map((item) => (
                      <div key={item.name} className="flex items-center gap-2">
                        <div className="h-3 w-3 rounded-full" style={{ backgroundColor: item.color }} />
                        <span className="text-sm text-gray-600 dark:text-gray-400">
                          {item.name}: {item.value}%
                        </span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Engagement Metrics */}
              <Card className="border-gray-200 dark:border-gray-800 lg:col-span-2">
                <CardHeader>
                  <CardTitle>Katılım Metrikleri</CardTitle>
                  <CardDescription>Toplantı katılım ve performans göstergeleri</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-6 md:grid-cols-3">
                    <div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Ortalama Katılım</p>
                      <div className="flex items-center gap-3">
                        <Progress value={aiAnalytics.averageAttendance} className="h-3" />
                        <span className="text-lg font-bold">{aiAnalytics.averageAttendance}%</span>
                      </div>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Etkileşim Skoru</p>
                      <div className="flex items-center gap-3">
                        <Progress value={aiAnalytics.engagementScore} className="h-3" />
                        <span className="text-lg font-bold">{aiAnalytics.engagementScore}%</span>
                      </div>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Toplam Katılımcı</p>
                      <div className="flex items-center gap-3">
                        <Users className="h-6 w-6 text-blue-500" />
                        <span className="text-lg font-bold">{aiAnalytics.totalParticipants}</span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}
