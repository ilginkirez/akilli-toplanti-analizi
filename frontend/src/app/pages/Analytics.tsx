import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '../components/ui/avatar';
import { Progress } from '../components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { 
  TrendingUp, TrendingDown, Users, CheckCircle2, AlertTriangle, 
  Trophy, Target, Clock, BarChart3
} from 'lucide-react';
import { mockPerformanceMetrics, mockTeamAnalytics, currentUser } from '../data/mockData';
import { getInitials, getWorkloadStatusColor, getWorkloadStatusLabel, getScoreColor } from '../utils/helpers';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  Legend
} from 'recharts';

export function Analytics() {
  const myMetrics = mockPerformanceMetrics.find(m => m.userId === currentUser.id);
  
  // Prepare chart data
  const performanceData = mockPerformanceMetrics.map(m => ({
    name: m.user.name.split(' ')[0],
    score: m.productivityScore,
    completionRate: m.completionRate,
    attendanceRate: m.attendanceRate
  }));

  const taskCompletionData = mockPerformanceMetrics.map(m => ({
    name: m.user.name.split(' ')[0],
    completed: m.tasksCompleted,
    overdue: m.tasksOverdue,
    pending: m.tasksAssigned - m.tasksCompleted - m.tasksOverdue
  }));

  const radarData = myMetrics ? [
    { metric: 'Tamamlanma', value: myMetrics.completionRate, fullMark: 100 },
    { metric: 'Katılım', value: myMetrics.attendanceRate, fullMark: 100 },
    { metric: 'Performans', value: myMetrics.productivityScore, fullMark: 100 },
    { metric: 'Konuşma', value: myMetrics.averageSpeakingTime * 2, fullMark: 100 },
    { metric: 'İş Yükü', value: myMetrics.workloadStatus === 'balanced' ? 80 : myMetrics.workloadStatus === 'overloaded' ? 40 : 60, fullMark: 100 }
  ] : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold bg-gradient-to-r from-gray-900 to-gray-700 dark:from-white dark:to-gray-300 bg-clip-text text-transparent">
          Analitik & Performans
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">
          Ekip ve kişisel performans metrikleri
        </p>
      </div>

      <Tabs defaultValue="personal" className="w-full">
        <TabsList>
          <TabsTrigger value="personal">Kişisel Performans</TabsTrigger>
          <TabsTrigger value="team">Ekip Analizi</TabsTrigger>
        </TabsList>

        {/* Personal Performance */}
        <TabsContent value="personal" className="space-y-6 mt-6">
          {/* Personal Stats */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card className="border-gray-200 dark:border-gray-800">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 dark:bg-blue-900/30">
                    <Target className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                  </div>
                  <TrendingUp className="h-4 w-4 text-green-500" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{myMetrics?.tasksCompleted || 0}</p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">Tamamlanan Görev</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {myMetrics?.tasksAssigned || 0} görevden
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="border-gray-200 dark:border-gray-800">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-100 dark:bg-green-900/30">
                    <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400" />
                  </div>
                  <span className="text-sm font-semibold text-green-600">{myMetrics?.completionRate || 0}%</span>
                </div>
                <div>
                  <p className="text-2xl font-bold">{myMetrics?.completionRate || 0}%</p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">Tamamlanma Oranı</p>
                  <Progress value={myMetrics?.completionRate || 0} className="h-2 mt-2" />
                </div>
              </CardContent>
            </Card>

            <Card className="border-gray-200 dark:border-gray-800">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-100 dark:bg-purple-900/30">
                    <Users className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                  </div>
                  <span className="text-sm font-semibold text-purple-600">{myMetrics?.attendanceRate || 0}%</span>
                </div>
                <div>
                  <p className="text-2xl font-bold">{myMetrics?.meetingsAttended || 0}</p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">Toplantı Katılımı</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {myMetrics?.meetingsScheduled || 0} toplantıdan
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="border-gray-200 dark:border-gray-800">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-yellow-100 dark:bg-yellow-900/30">
                    <Trophy className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
                  </div>
                  <TrendingUp className="h-4 w-4 text-green-500" />
                </div>
                <div>
                  <p className={`text-2xl font-bold ${getScoreColor(myMetrics?.productivityScore || 0)}`}>
                    {myMetrics?.productivityScore || 0}
                  </p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">Performans Skoru</p>
                  <p className="text-xs text-gray-500 mt-1">100 üzerinden</p>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            {/* Radar Chart */}
            <Card className="border-gray-200 dark:border-gray-800">
              <CardHeader>
                <CardTitle>Performans Dağılımı</CardTitle>
                <CardDescription>Farklı metriklerdeki performansınız</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart data={radarData}>
                      <PolarGrid />
                      <PolarAngleAxis dataKey="metric" />
                      <PolarRadiusAxis angle={90} domain={[0, 100]} />
                      <Radar name="Performans" dataKey="value" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.6} />
                      <Tooltip />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* Personal Insights */}
            <Card className="border-gray-200 dark:border-gray-800">
              <CardHeader>
                <CardTitle>Kişisel İçgörüler</CardTitle>
                <CardDescription>Son 7 günün özeti</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-start gap-3 p-4 rounded-lg bg-green-50 dark:bg-green-950/20 border border-green-200 dark:border-green-900">
                  <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400 mt-0.5" />
                  <div>
                    <h4 className="font-semibold text-sm">Yüksek Performans</h4>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      Bu hafta hedeflerinizin %{myMetrics?.completionRate || 0}'ini tamamladınız. Harika iş!
                    </p>
                  </div>
                </div>

                {myMetrics && myMetrics.tasksOverdue > 0 && (
                  <div className="flex items-start gap-3 p-4 rounded-lg bg-yellow-50 dark:bg-yellow-950/20 border border-yellow-200 dark:border-yellow-900">
                    <Clock className="h-5 w-5 text-yellow-600 dark:text-yellow-400 mt-0.5" />
                    <div>
                      <h4 className="font-semibold text-sm">Gecikmiş Görevler</h4>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                        {myMetrics.tasksOverdue} gecikmiş göreviniz var. Önceliklendirmeyi düşünün.
                      </p>
                    </div>
                  </div>
                )}

                <div className="flex items-start gap-3 p-4 rounded-lg bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-900">
                  <Users className="h-5 w-5 text-blue-600 dark:text-blue-400 mt-0.5" />
                  <div>
                    <h4 className="font-semibold text-sm">Toplantı Katılımı</h4>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      Toplantılara katılım oranınız %{myMetrics?.attendanceRate || 0}. Ortalama konuşma süreniz %{myMetrics?.averageSpeakingTime || 0}.
                    </p>
                  </div>
                </div>

                <div className="p-4 rounded-lg bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-950/20 dark:to-blue-950/20 border border-purple-200 dark:border-purple-900">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-semibold text-sm">İş Yükü Durumu</h4>
                    <Badge className={getWorkloadStatusColor(myMetrics?.workloadStatus || 'balanced')}>
                      {getWorkloadStatusLabel(myMetrics?.workloadStatus || 'balanced')}
                    </Badge>
                  </div>
                  <Progress 
                    value={
                      myMetrics?.workloadStatus === 'balanced' ? 70 :
                      myMetrics?.workloadStatus === 'overloaded' ? 95 : 40
                    } 
                    className="h-2" 
                  />
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Team Analysis */}
        <TabsContent value="team" className="space-y-6 mt-6">
          {/* Team Stats */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card className="border-gray-200 dark:border-gray-800">
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 dark:bg-blue-900/30">
                    <Users className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{mockTeamAnalytics.totalMeetings}</p>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Toplam Toplantı</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-gray-200 dark:border-gray-800">
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-100 dark:bg-green-900/30">
                    <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{mockTeamAnalytics.completedTasks}</p>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Tamamlanan Görev</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-gray-200 dark:border-gray-800">
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-100 dark:bg-red-900/30">
                    <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{mockTeamAnalytics.overdueTasks}</p>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Gecikmiş Görev</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-gray-200 dark:border-gray-800">
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-100 dark:bg-purple-900/30">
                    <BarChart3 className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{mockTeamAnalytics.teamProductivityScore}</p>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Ekip Skoru</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            {/* Performance Comparison */}
            <Card className="border-gray-200 dark:border-gray-800">
              <CardHeader>
                <CardTitle>Performans Karşılaştırması</CardTitle>
                <CardDescription>Ekip üyelerinin performans skorları</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={performanceData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis domain={[0, 100]} />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="score" fill="#3b82f6" name="Performans Skoru" />
                      <Bar dataKey="completionRate" fill="#10b981" name="Tamamlanma %" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* Task Distribution */}
            <Card className="border-gray-200 dark:border-gray-800">
              <CardHeader>
                <CardTitle>Görev Dağılımı</CardTitle>
                <CardDescription>Ekip üyelerinin görev durumları</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={taskCompletionData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="completed" stackId="a" fill="#10b981" name="Tamamlandı" />
                      <Bar dataKey="pending" stackId="a" fill="#3b82f6" name="Devam Eden" />
                      <Bar dataKey="overdue" stackId="a" fill="#ef4444" name="Gecikmiş" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Top Performers & Bottlenecks */}
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Top Performers */}
            <Card className="border-gray-200 dark:border-gray-800">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Trophy className="h-5 w-5 text-yellow-500" />
                  En İyi Performans
                </CardTitle>
                <CardDescription>Bu haftanın en başarılı ekip üyeleri</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {mockTeamAnalytics.topPerformers.map((performer, idx) => {
                    const user = mockPerformanceMetrics.find(m => m.userId === performer.userId)?.user;
                    return (
                      <div key={performer.userId} className="flex items-center gap-4">
                        <div className={`flex h-8 w-8 items-center justify-center rounded-full ${
                          idx === 0 ? 'bg-yellow-500' :
                          idx === 1 ? 'bg-gray-400' :
                          'bg-orange-600'
                        } text-white font-bold text-sm`}>
                          {idx + 1}
                        </div>
                        <Avatar className="h-10 w-10">
                          <AvatarImage src={user?.avatar} />
                          <AvatarFallback>{getInitials(performer.userName)}</AvatarFallback>
                        </Avatar>
                        <div className="flex-1">
                          <h4 className="font-semibold text-sm">{performer.userName}</h4>
                          <p className="text-xs text-gray-600 dark:text-gray-400">{user?.department}</p>
                        </div>
                        <div className="text-right">
                          <p className={`text-lg font-bold ${getScoreColor(performer.score)}`}>
                            {performer.score}
                          </p>
                          <p className="text-xs text-gray-600 dark:text-gray-400">Skor</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>

            {/* Bottlenecks */}
            <Card className="border-gray-200 dark:border-gray-800">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-orange-500" />
                  Darboğazlar & Uyarılar
                </CardTitle>
                <CardDescription>Dikkat gerektiren durumlar</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {mockTeamAnalytics.bottlenecks.map((bottleneck) => {
                    const user = mockPerformanceMetrics.find(m => m.userId === bottleneck.userId)?.user;
                    return (
                      <div
                        key={bottleneck.userId}
                        className={`flex items-start gap-3 p-4 rounded-lg border ${
                          bottleneck.severity === 'high'
                            ? 'bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-900'
                            : bottleneck.severity === 'medium'
                            ? 'bg-yellow-50 dark:bg-yellow-950/20 border-yellow-200 dark:border-yellow-900'
                            : 'bg-blue-50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-900'
                        }`}
                      >
                        <Avatar className="h-10 w-10">
                          <AvatarImage src={user?.avatar} />
                          <AvatarFallback>{getInitials(bottleneck.userName)}</AvatarFallback>
                        </Avatar>
                        <div className="flex-1">
                          <div className="flex items-center justify-between mb-1">
                            <h4 className="font-semibold text-sm">{bottleneck.userName}</h4>
                            <Badge variant={
                              bottleneck.severity === 'high' ? 'destructive' :
                              bottleneck.severity === 'medium' ? 'default' :
                              'secondary'
                            }>
                              {bottleneck.severity === 'high' ? 'Yüksek' :
                               bottleneck.severity === 'medium' ? 'Orta' : 'Düşük'}
                            </Badge>
                          </div>
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            {bottleneck.issue}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
