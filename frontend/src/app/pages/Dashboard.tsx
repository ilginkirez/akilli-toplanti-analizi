import { Link } from 'react-router';
import {
  AlertCircle,
  ArrowRight,
  Calendar,
  CheckCircle2,
  Clock,
  Sparkles,
  TrendingUp,
  Users,
} from 'lucide-react';
import { BarChart, Bar, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { Avatar, AvatarFallback, AvatarImage } from '../components/ui/avatar';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Progress } from '../components/ui/progress';
import { useAuth } from '../auth/AuthContext';
import { useMeetings } from '../meetings/MeetingsContext';
import { currentUser, mockPerformanceMetrics, mockTasks, mockUsers } from '../data/mockData';
import {
  getInitials,
  getMeetingStatusColor,
  getMeetingStatusLabel,
  getRelativeTime,
  getScoreColor,
  getTaskStatusColor,
  getTaskStatusLabel,
} from '../utils/helpers';

export function Dashboard() {
  const { user } = useAuth();
  const { meetings } = useMeetings();

  const dataUser =
    mockUsers.find((candidate) =>
      user
        ? candidate.email.toLowerCase() === user.email.toLowerCase() ||
          candidate.name.toLowerCase() === user.name.toLowerCase()
        : false,
    ) ?? currentUser;

  const upcomingMeetings = meetings
    .filter((meeting) => meeting.status === 'upcoming')
    .sort((left, right) => left.startTime.getTime() - right.startTime.getTime())
    .slice(0, 3);

  const myTasks = mockTasks
    .filter((task) => task.assignee.id === dataUser.id && task.status !== 'completed')
    .sort((left, right) => {
      if (left.status === 'overdue' && right.status !== 'overdue') return -1;
      if (left.status !== 'overdue' && right.status === 'overdue') return 1;
      return left.dueDate.getTime() - right.dueDate.getTime();
    })
    .slice(0, 5);

  const myMetrics = mockPerformanceMetrics.find((metric) => metric.userId === dataUser.id);

  const recentMeetings = meetings
    .filter((meeting) => meeting.status === 'completed')
    .sort((left, right) => right.startTime.getTime() - left.startTime.getTime())
    .slice(0, 2);

  const taskChartData = [
    { name: 'Tamamlandı', value: myMetrics?.tasksCompleted || 0, color: '#10b981' },
    {
      name: 'Devam Eden',
      value:
        (myMetrics?.tasksAssigned || 0) -
        (myMetrics?.tasksCompleted || 0) -
        (myMetrics?.tasksOverdue || 0),
      color: '#3b82f6',
    },
    { name: 'Gecikmiş', value: myMetrics?.tasksOverdue || 0, color: '#ef4444' },
  ];

  const meetingVolumeData = upcomingMeetings.map((meeting) => ({
    name: meeting.title.split(' ').slice(0, 2).join(' '),
    participants: meeting.participants.length,
  }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-3xl font-bold text-transparent dark:from-white dark:to-gray-300">
          Hoş Geldiniz, {(user?.name ?? dataUser.name).split(' ')[0]}
        </h1>
        <p className="mt-1 text-gray-600 dark:text-gray-400">
          Bugünkü toplantı ve görev akışı burada sizi bekliyor.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="border-gray-200 bg-gradient-to-br from-white to-gray-50 dark:border-gray-800 dark:from-gray-900 dark:to-gray-950">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Yaklaşan Toplantılar</CardTitle>
            <Calendar className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{upcomingMeetings.length}</div>
            <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">Bu hafta</p>
          </CardContent>
        </Card>

        <Card className="border-gray-200 bg-gradient-to-br from-white to-gray-50 dark:border-gray-800 dark:from-gray-900 dark:to-gray-950">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Aktif Görevler</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{myTasks.length}</div>
            <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
              {myMetrics?.tasksOverdue || 0} gecikmiş
            </p>
          </CardContent>
        </Card>

        <Card className="border-gray-200 bg-gradient-to-br from-white to-gray-50 dark:border-gray-800 dark:from-gray-900 dark:to-gray-950">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Tamamlanma Oranı</CardTitle>
            <TrendingUp className="h-4 w-4 text-purple-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{myMetrics?.completionRate || 0}%</div>
            <Progress value={myMetrics?.completionRate || 0} className="mt-2 h-2" />
          </CardContent>
        </Card>

        <Card className="border-gray-200 bg-gradient-to-br from-white to-gray-50 dark:border-gray-800 dark:from-gray-900 dark:to-gray-950">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Performans Skoru</CardTitle>
            <Sparkles className="h-4 w-4 text-yellow-600" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${getScoreColor(myMetrics?.productivityScore || 0)}`}>
              {myMetrics?.productivityScore || 0}
            </div>
            <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">100 üzerinden</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="border-gray-200 dark:border-gray-800">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Yaklaşan Toplantılar</CardTitle>
                <CardDescription>Gelecek birkaç günde sizi bekleyen oturumlar</CardDescription>
              </div>
              <Link to="/meetings">
                <Button variant="ghost" size="sm">
                  Tümünü Gör
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {upcomingMeetings.length === 0 ? (
              <div className="py-8 text-center text-gray-500 dark:text-gray-400">
                <Calendar className="mx-auto mb-3 h-12 w-12 opacity-50" />
                <p>Yaklaşan toplantı yok.</p>
              </div>
            ) : (
              upcomingMeetings.map((meeting) => (
                <Link key={meeting.id} to={`/meetings/${meeting.id}`}>
                  <div className="cursor-pointer rounded-xl border border-gray-200 p-4 transition-colors hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-900">
                    <div className="flex items-start gap-4">
                      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 shadow-lg shadow-blue-500/20">
                        <Calendar className="h-6 w-6 text-white" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-start justify-between gap-2">
                          <h4 className="text-sm font-semibold">{meeting.title}</h4>
                          <Badge className={getMeetingStatusColor(meeting.status)}>
                            {getMeetingStatusLabel(meeting.status)}
                          </Badge>
                        </div>
                        <div className="mt-2 flex items-center gap-4 text-xs text-gray-600 dark:text-gray-400">
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {getRelativeTime(meeting.startTime)}
                          </span>
                          <span className="flex items-center gap-1">
                            <Users className="h-3 w-3" />
                            {meeting.participants.length} kişi
                          </span>
                        </div>
                        <div className="mt-2 flex items-center gap-1">
                          {meeting.participants.slice(0, 3).map((participant) => (
                            <Avatar key={participant.user.id} className="h-6 w-6 border-2 border-white dark:border-gray-900">
                              <AvatarImage src={participant.user.avatar} />
                              <AvatarFallback className="text-xs">
                                {getInitials(participant.user.name)}
                              </AvatarFallback>
                            </Avatar>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                </Link>
              ))
            )}
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-800">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Görevlerim</CardTitle>
                <CardDescription>Bekleyen ve devam eden işler</CardDescription>
              </div>
              <Link to="/tasks">
                <Button variant="ghost" size="sm">
                  Tümünü Gör
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {myTasks.length === 0 ? (
              <div className="py-8 text-center text-gray-500 dark:text-gray-400">
                <CheckCircle2 className="mx-auto mb-3 h-12 w-12 opacity-50" />
                <p>Bekleyen görev yok.</p>
              </div>
            ) : (
              myTasks.map((task) => (
                <div
                  key={task.id}
                  className="flex items-start gap-3 rounded-lg border border-gray-200 p-3 transition-colors hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-900"
                >
                  <div className="mt-1">
                    {task.status === 'overdue' ? (
                      <AlertCircle className="h-4 w-4 text-red-500" />
                    ) : (
                      <div className="h-4 w-4 rounded border-2 border-gray-300 dark:border-gray-700" />
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-2">
                      <h4 className="text-sm font-medium">{task.title}</h4>
                      <Badge className={getTaskStatusColor(task.status)} variant="secondary">
                        {getTaskStatusLabel(task.status)}
                      </Badge>
                    </div>
                    <div className="mt-1 flex items-center gap-3 text-xs text-gray-600 dark:text-gray-400">
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {getRelativeTime(task.dueDate)}
                      </span>
                      {task.sourceType === 'ai-generated' && (
                        <Badge variant="outline" className="h-5 text-xs">
                          <Sparkles className="mr-1 h-3 w-3" />
                          AI
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="border-gray-200 dark:border-gray-800 lg:col-span-2">
          <CardHeader>
            <CardTitle>Görev Dağılımı</CardTitle>
            <CardDescription>Son haftadaki iş durumu</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={taskChartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={90}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {taskChartData.map((entry, index) => (
                      <Cell key={`task-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-4 flex justify-center gap-6">
              {taskChartData.map((item) => (
                <div key={item.name} className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded-full" style={{ backgroundColor: item.color }} />
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    {item.name}: {item.value}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-800">
          <CardHeader>
            <CardTitle>Son AI Özeti</CardTitle>
            <CardDescription>En son tamamlanan toplantı</CardDescription>
          </CardHeader>
          <CardContent>
            {recentMeetings.length > 0 && recentMeetings[0].aiSummary ? (
              <div className="space-y-4">
                <div>
                  <h4 className="mb-2 text-sm font-semibold">{recentMeetings[0].title}</h4>
                  <p className="line-clamp-4 text-sm text-gray-600 dark:text-gray-400">
                    {recentMeetings[0].aiSummary.executiveSummary}
                  </p>
                </div>
                <div>
                  <h5 className="mb-2 text-xs font-semibold text-gray-700 dark:text-gray-300">
                    Önemli Kararlar
                  </h5>
                  <ul className="space-y-1">
                    {recentMeetings[0].aiSummary.keyDecisions.slice(0, 2).map((decision, index) => (
                      <li key={index} className="flex items-start gap-2 text-xs text-gray-600 dark:text-gray-400">
                        <CheckCircle2 className="mt-0.5 h-3 w-3 flex-shrink-0 text-green-500" />
                        {decision}
                      </li>
                    ))}
                  </ul>
                </div>
                <Link to={`/meetings/${recentMeetings[0].id}`}>
                  <Button variant="outline" size="sm" className="w-full">
                    Detayları Gör
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="py-8 text-center text-gray-500 dark:text-gray-400">
                <Sparkles className="mx-auto mb-3 h-12 w-12 opacity-50" />
                <p className="text-sm">Henüz AI özeti yok.</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="border-gray-200 dark:border-gray-800">
        <CardHeader>
          <CardTitle>Toplantı Kapasitesi</CardTitle>
          <CardDescription>Yaklaşan toplantı bazında katılımcı yoğunluğu</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={meetingVolumeData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="participants" fill="#6366f1" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
