import { User, Meeting, Task, PerformanceMetrics, TeamAnalytics, MeetingAnalytics, AISummary, Transcript, SpeechSegment } from '../types';

// Mock Users
export const mockUsers: User[] = [
  {
    id: '1',
    name: 'Ahmet Yılmaz',
    email: 'ahmet.yilmaz@company.com',
    avatar: 'https://i.pravatar.cc/150?img=12',
    role: 'manager',
    department: 'Ürün Geliştirme'
  },
  {
    id: '2',
    name: 'Zeynep Kara',
    email: 'zeynep.kara@company.com',
    avatar: 'https://i.pravatar.cc/150?img=45',
    role: 'member',
    department: 'Tasarım'
  },
  {
    id: '3',
    name: 'Mehmet Demir',
    email: 'mehmet.demir@company.com',
    avatar: 'https://i.pravatar.cc/150?img=33',
    role: 'member',
    department: 'Mühendislik'
  },
  {
    id: '4',
    name: 'Ayşe Şahin',
    email: 'ayse.sahin@company.com',
    avatar: 'https://i.pravatar.cc/150?img=47',
    role: 'admin',
    department: 'Operasyon'
  },
  {
    id: '5',
    name: 'Can Öztürk',
    email: 'can.ozturk@company.com',
    avatar: 'https://i.pravatar.cc/150?img=15',
    role: 'member',
    department: 'Mühendislik'
  },
  {
    id: '6',
    name: 'Elif Arslan',
    email: 'elif.arslan@company.com',
    avatar: 'https://i.pravatar.cc/150?img=23',
    role: 'member',
    department: 'Pazarlama'
  }
];

// Mock Speech Segments
const mockSegments: SpeechSegment[] = [
  {
    id: 's1',
    speaker: mockUsers[0],
    text: 'Günaydın ekip. Bugünkü toplantımızda Q2 hedeflerimizi ve yeni ürün özelliklerini konuşacağız.',
    startTime: 0,
    endTime: 8,
    sentiment: 'positive',
    confidence: 0.95
  },
  {
    id: 's2',
    speaker: mockUsers[1],
    text: 'Tasarım tarafında yeni kullanıcı arayüzü prototipleri hazır. Bu hafta içinde sunacağım.',
    startTime: 10,
    endTime: 18,
    sentiment: 'positive',
    confidence: 0.92
  },
  {
    id: 's3',
    speaker: mockUsers[2],
    text: 'Backend entegrasyonunda bazı gecikme yaşadık. API optimizasyonu için 3 gün daha lazım.',
    startTime: 20,
    endTime: 28,
    sentiment: 'neutral',
    confidence: 0.89
  },
  {
    id: 's4',
    speaker: mockUsers[0],
    text: 'Anladım Mehmet. O zaman önceliği performance iyileştirmelerine verelim. Zeynep, tasarımları pazartesiye kadar paylaşabilir misin?',
    startTime: 30,
    endTime: 40,
    sentiment: 'neutral',
    confidence: 0.94
  },
  {
    id: 's5',
    speaker: mockUsers[1],
    text: 'Evet, sorun değil. Cuma gününe kadar tamamlarım.',
    startTime: 42,
    endTime: 46,
    sentiment: 'positive',
    confidence: 0.96
  }
];

// Mock Transcript
const mockTranscript: Transcript = {
  id: 't1',
  meetingId: 'm1',
  segments: mockSegments,
  fullText: mockSegments.map(s => `${s.speaker.name}: ${s.text}`).join('\n')
};

// Mock AI Summary
const mockAISummary: AISummary = {
  executiveSummary: 'Ekip Q2 hedeflerini ve yeni ürün özelliklerini değerlendirdi. Tasarım ekibi prototipleri tamamlamış durumda, ancak backend entegrasyonunda 3 günlük gecikme bekleniyor. Öncelik performance optimizasyonuna verildi.',
  keyDecisions: [
    'Performance iyileştirmeleri önceliklendirildi',
    'Tasarım prototipleri Cuma gününe kadar tamamlanacak',
    'Backend API optimizasyonu için 3 gün ek süre verildi',
    'Gelecek toplantı tarihini Pazartesiye ertelendi'
  ],
  actionItems: [],
  topics: ['Q2 Hedefleri', 'Ürün Özellikleri', 'Backend Entegrasyonu', 'Tasarım Prototipleri'],
  sentiment: 'positive',
  agendaAdherence: 87
};

// Mock Meeting Analytics
const mockMeetingAnalytics: MeetingAnalytics = {
  totalParticipants: 4,
  averageAttendance: 92,
  speakingDistribution: [
    { userId: '1', userName: 'Ahmet Yılmaz', percentage: 35, duration: 180 },
    { userId: '2', userName: 'Zeynep Kara', percentage: 25, duration: 130 },
    { userId: '3', userName: 'Mehmet Demir', percentage: 28, duration: 145 },
    { userId: '4', userName: 'Ayşe Şahin', percentage: 12, duration: 62 }
  ],
  engagementScore: 88,
  sentimentBreakdown: {
    positive: 65,
    neutral: 30,
    negative: 5
  }
};

// Mock Meetings
export const mockMeetings: Meeting[] = [
  {
    id: 'm1',
    title: 'Q2 Strateji Toplantısı',
    description: 'İkinci çeyrek hedefleri ve yeni ürün özellikleri değerlendirmesi',
    startTime: new Date('2026-04-14T10:00:00'),
    endTime: new Date('2026-04-14T11:30:00'),
    status: 'completed',
    organizer: mockUsers[0],
    participants: [
      { user: mockUsers[0], status: 'accepted', joinedAt: new Date('2026-04-14T10:00:00'), speakingTime: 180, cameraOnTime: 5400, micOnTime: 5400 },
      { user: mockUsers[1], status: 'accepted', joinedAt: new Date('2026-04-14T10:02:00'), speakingTime: 130, cameraOnTime: 5280, micOnTime: 5280 },
      { user: mockUsers[2], status: 'accepted', joinedAt: new Date('2026-04-14T10:01:00'), speakingTime: 145, cameraOnTime: 5340, micOnTime: 5340 },
      { user: mockUsers[3], status: 'accepted', joinedAt: new Date('2026-04-14T10:03:00'), speakingTime: 62, cameraOnTime: 5220, micOnTime: 5220 }
    ],
    agenda: [
      { id: 'a1', title: 'Q2 Hedefleri Gözden Geçirme', duration: 30, completed: true },
      { id: 'a2', title: 'Yeni Ürün Özellikleri', duration: 45, completed: true },
      { id: 'a3', title: 'Ekip Görev Dağılımı', duration: 15, completed: true }
    ],
    transcript: mockTranscript,
    aiSummary: mockAISummary,
    aiAnalytics: mockMeetingAnalytics
  },
  {
    id: 'm2',
    title: 'Haftalık Sync - Tasarım Ekibi',
    description: 'Tasarım ekibi haftalık ilerleme toplantısı',
    startTime: new Date('2026-04-16T14:00:00'),
    endTime: new Date('2026-04-16T15:00:00'),
    status: 'upcoming',
    organizer: mockUsers[1],
    participants: [
      { user: mockUsers[1], status: 'accepted' },
      { user: mockUsers[0], status: 'accepted' },
      { user: mockUsers[5], status: 'pending' }
    ],
    agenda: [
      { id: 'a4', title: 'Prototip İncelemeleri', duration: 30, completed: false },
      { id: 'a5', title: 'Kullanıcı Geri Bildirimleri', duration: 20, completed: false },
      { id: 'a6', title: 'Gelecek Sprint Planı', duration: 10, completed: false }
    ]
  },
  {
    id: 'm3',
    title: 'Sprint Planning - Mühendislik',
    description: 'Yeni sprint için görev planlama toplantısı',
    startTime: new Date('2026-04-17T10:00:00'),
    endTime: new Date('2026-04-17T12:00:00'),
    status: 'upcoming',
    organizer: mockUsers[0],
    participants: [
      { user: mockUsers[0], status: 'accepted' },
      { user: mockUsers[2], status: 'accepted' },
      { user: mockUsers[4], status: 'accepted' },
      { user: mockUsers[3], status: 'pending' }
    ],
    agenda: [
      { id: 'a7', title: 'Sprint Hedefleri', duration: 30, completed: false },
      { id: 'a8', title: 'Görev Tahminleme', duration: 60, completed: false },
      { id: 'a9', title: 'Kapasile Planlaması', duration: 30, completed: false }
    ]
  },
  {
    id: 'm4',
    title: 'Müşteri Demo Sunumu',
    description: 'Yeni özelliklerin müşteriye tanıtımı',
    startTime: new Date('2026-04-18T15:00:00'),
    endTime: new Date('2026-04-18T16:00:00'),
    status: 'upcoming',
    organizer: mockUsers[3],
    participants: [
      { user: mockUsers[3], status: 'accepted' },
      { user: mockUsers[0], status: 'accepted' },
      { user: mockUsers[1], status: 'accepted' }
    ],
    agenda: [
      { id: 'a10', title: 'Demo Hazırlık', duration: 15, completed: false },
      { id: 'a11', title: 'Canlı Demo', duration: 30, completed: false },
      { id: 'a12', title: 'Soru & Cevap', duration: 15, completed: false }
    ]
  },
  {
    id: 'm5',
    title: 'Aylık Performans Değerlendirme',
    description: 'Mart ayı performans metrikleri ve analiz',
    startTime: new Date('2026-04-10T09:00:00'),
    endTime: new Date('2026-04-10T10:30:00'),
    status: 'completed',
    organizer: mockUsers[3],
    participants: [
      { user: mockUsers[3], status: 'accepted', joinedAt: new Date('2026-04-10T09:00:00'), speakingTime: 210, cameraOnTime: 5400, micOnTime: 5400 },
      { user: mockUsers[0], status: 'accepted', joinedAt: new Date('2026-04-10T09:01:00'), speakingTime: 180, cameraOnTime: 5340, micOnTime: 5340 },
      { user: mockUsers[1], status: 'accepted', joinedAt: new Date('2026-04-10T09:00:00'), speakingTime: 95, cameraOnTime: 5400, micOnTime: 5400 },
      { user: mockUsers[2], status: 'accepted', joinedAt: new Date('2026-04-10T09:02:00'), speakingTime: 110, cameraOnTime: 5280, micOnTime: 5280 }
    ],
    agenda: [
      { id: 'a13', title: 'Mart Ayı Sonuçları', duration: 45, completed: true },
      { id: 'a14', title: 'İyileştirme Alanları', duration: 30, completed: true },
      { id: 'a15', title: 'Nisan Hedefleri', duration: 15, completed: true }
    ],
    aiSummary: {
      executiveSummary: 'Mart ayında ekip hedeflerinin %94\'ünü başarıyla tamamladı. Müşteri memnuniyeti skorları yükseldi. Nisan ayı için agresif büyüme hedefleri belirlendi.',
      keyDecisions: [
        'Ekip büyüklüğüne 2 yeni mühendis eklenmesi onaylandı',
        'Otomatize test coverage %80\'e çıkarılacak',
        'Haftalık sync toplantıları 45 dakikaya indirilecek'
      ],
      actionItems: [],
      topics: ['Mart Performansı', 'Büyüme Stratejisi', 'Ekip Genişletme'],
      sentiment: 'positive',
      agendaAdherence: 95
    }
  }
];

// Mock Tasks
export const mockTasks: Task[] = [
  {
    title: 'Yeni kullan�c� aray�z� prototipleri haz�rla',
    description: 'Yeni dashboard tasar�mlar�n� tamamla ve ekiple payla�',
    assignee: mockUsers[1],
    assigner: mockUsers[0],
    dueDate: new Date('2026-04-19T17:00:00'),
    status: 'in-progress',
    priority: 'high',
    sourceType: 'ai-generated',
    meetingId: 'm1',
    createdAt: new Date('2026-04-14T11:30:00'),
    tags: ['tasarım', 'ui/ux', 'prototip']
  },
  {
    id: 't2',
    title: 'Backend API optimizasyonu',
    description: 'Veritabanı sorgularını optimize et ve response time\'ı iyileştir',
    assignee: mockUsers[2],
    assigner: mockUsers[0],
    dueDate: new Date('2026-04-17T17:00:00'),
    status: 'in-progress',
    priority: 'urgent',
    sourceType: 'ai-generated',
    meetingId: 'm1',
    createdAt: new Date('2026-04-14T11:30:00'),
    tags: ['backend', 'performance', 'api']
  },
  {
    id: 't3',
    title: 'Q2 hedeflerini dokümante et',
    description: 'Tüm ekip hedeflerini Confluence\'a yaz ve paylaş',
    assignee: mockUsers[0],
    dueDate: new Date('2026-04-16T17:00:00'),
    status: 'completed',
    priority: 'medium',
    sourceType: 'ai-generated',
    meetingId: 'm1',
    createdAt: new Date('2026-04-14T11:30:00'),
    completedAt: new Date('2026-04-15T14:20:00'),
    tags: ['dokümantasyon', 'planlama']
  },
  {
    id: 't4',
    title: 'Mobil uygulama bildirimleri implementasyonu',
    description: 'Push notification servisi entegrasyonu ve test edilmesi',
    assignee: mockUsers[4],
    assigner: mockUsers[0],
    dueDate: new Date('2026-04-20T17:00:00'),
    status: 'todo',
    priority: 'medium',
    sourceType: 'manual',
    createdAt: new Date('2026-04-15T09:00:00'),
    tags: ['mobil', 'notification', 'feature']
  },
  {
    id: 't5',
    title: 'Güvenlik audit raporu hazırla',
    description: 'Sistemin security vulnerability taraması ve rapor hazırlama',
    assignee: mockUsers[4],
    assigner: mockUsers[3],
    dueDate: new Date('2026-04-18T17:00:00'),
    status: 'in-progress',
    priority: 'high',
    sourceType: 'manual',
    createdAt: new Date('2026-04-12T10:00:00'),
    tags: ['güvenlik', 'audit', 'compliance']
  },
  {
    id: 't6',
    title: 'Pazarlama materyalleri tasarımı',
    description: 'Yeni ürün lansmanı için sosyal medya görselleri',
    assignee: mockUsers[5],
    assigner: mockUsers[3],
    dueDate: new Date('2026-04-22T17:00:00'),
    status: 'todo',
    priority: 'medium',
    sourceType: 'manual',
    createdAt: new Date('2026-04-15T11:00:00'),
    tags: ['pazarlama', 'tasarım', 'sosyal-medya']
  },
  {
    id: 't7',
    title: 'Unit test coverage artır',
    description: 'Backend servislerinde test coverage\'ı %80\'e çıkar',
    assignee: mockUsers[2],
    assigner: mockUsers[0],
    dueDate: new Date('2026-04-12T17:00:00'),
    status: 'overdue',
    priority: 'high',
    sourceType: 'manual',
    createdAt: new Date('2026-04-08T09:00:00'),
    tags: ['test', 'kalite', 'backend']
  },
  {
    id: 't8',
    title: 'Kullanıcı dokümantasyonu güncelle',
    description: 'Yeni özellikler için kullanıcı kılavuzu yaz',
    assignee: mockUsers[1],
    assigner: mockUsers[3],
    dueDate: new Date('2026-04-21T17:00:00'),
    status: 'todo',
    priority: 'low',
    sourceType: 'manual',
    createdAt: new Date('2026-04-14T15:00:00'),
    tags: ['dokümantasyon', 'kullanıcı']
  }
];

// Update AI summaries with actual tasks
mockMeetings[0].aiSummary!.actionItems = [mockTasks[0], mockTasks[1], mockTasks[2]];

// Mock Performance Metrics
export const mockPerformanceMetrics: PerformanceMetrics[] = [
  {
    userId: '1',
    user: mockUsers[0],
    period: {
      start: new Date('2026-04-07T00:00:00'),
      end: new Date('2026-04-13T23:59:59')
    },
    tasksAssigned: 5,
    tasksCompleted: 4,
    tasksOverdue: 0,
    completionRate: 80,
    meetingsAttended: 8,
    meetingsScheduled: 10,
    attendanceRate: 95,
    averageSpeakingTime: 32,
    productivityScore: 88,
    workloadStatus: 'balanced'
  },
  {
    userId: '2',
    user: mockUsers[1],
    period: {
      start: new Date('2026-04-07T00:00:00'),
      end: new Date('2026-04-13T23:59:59')
    },
    tasksAssigned: 6,
    tasksCompleted: 5,
    tasksOverdue: 0,
    completionRate: 83,
    meetingsAttended: 6,
    meetingsScheduled: 7,
    attendanceRate: 86,
    averageSpeakingTime: 18,
    productivityScore: 85,
    workloadStatus: 'balanced'
  },
  {
    userId: '3',
    user: mockUsers[2],
    period: {
      start: new Date('2026-04-07T00:00:00'),
      end: new Date('2026-04-13T23:59:59')
    },
    tasksAssigned: 8,
    tasksCompleted: 5,
    tasksOverdue: 2,
    completionRate: 62,
    meetingsAttended: 7,
    meetingsScheduled: 8,
    attendanceRate: 88,
    averageSpeakingTime: 25,
    productivityScore: 68,
    workloadStatus: 'overloaded'
  },
  {
    userId: '4',
    user: mockUsers[3],
    period: {
      start: new Date('2026-04-07T00:00:00'),
      end: new Date('2026-04-13T23:59:59')
    },
    tasksAssigned: 4,
    tasksCompleted: 4,
    tasksOverdue: 0,
    completionRate: 100,
    meetingsAttended: 10,
    meetingsScheduled: 10,
    attendanceRate: 100,
    averageSpeakingTime: 28,
    productivityScore: 95,
    workloadStatus: 'balanced'
  },
  {
    userId: '5',
    user: mockUsers[4],
    period: {
      start: new Date('2026-04-07T00:00:00'),
      end: new Date('2026-04-13T23:59:59')
    },
    tasksAssigned: 7,
    tasksCompleted: 6,
    tasksOverdue: 1,
    completionRate: 86,
    meetingsAttended: 5,
    meetingsScheduled: 6,
    attendanceRate: 83,
    averageSpeakingTime: 22,
    productivityScore: 82,
    workloadStatus: 'balanced'
  },
  {
    userId: '6',
    user: mockUsers[5],
    period: {
      start: new Date('2026-04-07T00:00:00'),
      end: new Date('2026-04-13T23:59:59')
    },
    tasksAssigned: 3,
    tasksCompleted: 2,
    tasksOverdue: 0,
    completionRate: 67,
    meetingsAttended: 4,
    meetingsScheduled: 5,
    attendanceRate: 80,
    averageSpeakingTime: 15,
    productivityScore: 72,
    workloadStatus: 'underloaded'
  }
];

// Mock Team Analytics
export const mockTeamAnalytics: TeamAnalytics = {
  period: {
    start: new Date('2026-04-07T00:00:00'),
    end: new Date('2026-04-13T23:59:59')
  },
  totalMeetings: 12,
  totalTasks: 33,
  completedTasks: 26,
  overdueTasks: 3,
  teamProductivityScore: 82,
  bottlenecks: [
    {
      userId: '3',
      userName: 'Mehmet Demir',
      issue: 'Aşırı iş yükü - 8 aktif görev, 2 gecikmiş',
      severity: 'high'
    },
    {
      userId: '6',
      userName: 'Elif Arslan',
      issue: 'Düşük kapasite kullanımı - Sadece 3 görev',
      severity: 'low'
    }
  ],
  topPerformers: [
    { userId: '4', userName: 'Ayşe Şahin', score: 95 },
    { userId: '1', userName: 'Ahmet Yılmaz', score: 88 },
    { userId: '2', userName: 'Zeynep Kara', score: 85 }
  ]
};

// Current user (for the app)
export const currentUser = mockUsers[0];


