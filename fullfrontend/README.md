# MeetingAI - Akıllı Toplantı ve Ekip Performans Yönetim Sistemi

## 🌟 Genel Bakış

MeetingAI, yapay zeka destekli akıllı bir toplantı ve ekip performans yönetim platformudur. Video konferans, gerçek zamanlı transkripsiyon, AI analizi ve görev yönetimi özelliklerini tek bir platformda birleştirir.

## ✨ Özellikler

### 1. Toplantı Öncesi (Planlama ve Organizasyon)
- ✅ Toplantı planlama ekranı (tarih, saat, gündem)
- ✅ Katılımcı davet sistemi ve durum takibi
- ✅ Takvim görünümü
- ✅ "Toplantılarım" dashboard'u

### 2. Toplantı Esnası (İletişim ve Veri Toplama)
- 🔄 Video konferans lobby (Mock - WebRTC/LiveKit entegrasyonu için hazır)
- 🔄 Kişi bazlı ses kaydı ve STT (Mock data ile gösterim)
- ✅ Gerçek zamanlı metin akışı görünümü

### 3. Toplantı Sonrası (Yapay Zeka Analizi)
- ✅ Otomatik görev çıkarımı ve ataması (AI Generated)
- ✅ Toplantı özeti ve karar defteri
- ✅ Konuşma ve katılım analizleri
- ✅ Duygu ve gündem analizi
- ✅ Konuşma dominasyon analizi

### 4. Performans ve Görev Yönetimi
- ✅ Kişisel ve ekip performans paneli
- ✅ İş yükü ve darboğaz tespit uyarısı
- ✅ Kanban/Liste görev görünümü (Drag & Drop)
- ✅ Haftalık/Aylık takip metrikleri

## 🎨 Tasarım Özellikleri

- **Modern & Premium UI**: Glassmorphism, gradient efektleri, mikro animasyonlar
- **Dark/Light Mode**: Tam tema desteği
- **Responsive Design**: Tüm ekran boyutlarında optimize
- **Inter Font**: Premium tipografi
- **Renkli Metrikler**: Görsel performans göstergeleri

## 📊 Veri Modelleri

### Temel Modeller
- **User**: Kullanıcı bilgileri ve rolleri
- **Meeting**: Toplantı detayları ve durumu
- **Task**: Görev yönetimi ve takibi
- **Transcript**: Konuşma transkriptleri
- **PerformanceMetrics**: Performans metrikleri
- **TeamAnalytics**: Ekip analitikleri

## 🛠️ Teknoloji Stack

- **React 18**: Modern UI framework
- **TypeScript**: Type-safe development
- **React Router v7**: Data mode routing
- **Tailwind CSS v4**: Utility-first styling
- **Recharts**: Data visualization
- **React DnD**: Drag and drop (Kanban)
- **date-fns**: Date formatting (Turkish locale)
- **Lucide React**: Icon system
- **Radix UI**: Accessible components
- **Motion**: Animation library

## 📁 Proje Yapısı

```
src/app/
├── components/
│   ├── Layout.tsx          # Ana layout ve navigasyon
│   └── ui/                 # Tüm UI bileşenleri
├── pages/
│   ├── Dashboard.tsx       # Ana dashboard
│   ├── Meetings.tsx        # Toplantı listesi
│   ├── MeetingDetail.tsx   # Toplantı detay ve AI analizi
│   ├── CreateMeeting.tsx   # Yeni toplantı oluşturma
│   ├── Tasks.tsx           # Görev yönetimi (Kanban)
│   ├── Analytics.tsx       # Performans analitikleri
│   └── NotFound.tsx        # 404 sayfası
├── data/
│   └── mockData.ts         # Mock veriler
├── types/
│   └── index.ts            # TypeScript type definitions
├── utils/
│   └── helpers.ts          # Yardımcı fonksiyonlar
└── routes.tsx              # Route yapılandırması
```

## 🚀 Gelecek Geliştirmeler

### Backend Entegrasyonu (Supabase ile)
- Gerçek kullanıcı kimlik doğrulama
- Veritabanı persistency
- Gerçek zamanlı senkronizasyon
- Dosya depolama (ses kayıtları)

### Video Konferans
- WebRTC entegrasyonu (LiveKit/Agora)
- Gerçek zamanlı video/ses iletişimi
- Ekran paylaşımı

### AI/ML Entegrasyonları
- OpenAI GPT-4 entegrasyonu (özet, karar çıkarımı)
- Whisper API (Speech-to-Text)
- Speaker Diarization
- Sentiment Analysis API

### Ek Özellikler
- Email bildirimleri
- Takvim senkronizasyonu (Google Calendar, Outlook)
- Export özellikleri (PDF, Excel)
- Mobil uygulama

## 💡 Kullanım

### Ana Dashboard
- Yaklaşan toplantılarınızı görün
- Görevlerinizi takip edin
- Performans metriklerinizi izleyin

### Toplantı Oluşturma
1. "Yeni Toplantı" butonuna tıklayın
2. Başlık, tarih ve saat belirleyin
3. Katılımcıları ekleyin
4. Gündem maddelerini oluşturun
5. Davet gönderin

### Görev Yönetimi
- Kanban board ile sürükle-bırak görev yönetimi
- AI tarafından otomatik oluşturulan görevler
- Priorite ve durum takibi

### Analytics
- Kişisel performans metrikleri
- Ekip karşılaştırmaları
- Darboğaz tespiti
- En iyi performans göstergeleri

## 🔐 Güvenlik Notu

Bu proje şu anda frontend-only bir demo'dur. Production ortamında:
- Supabase veya benzeri backend servisi kullanın
- Row Level Security (RLS) politikaları uygulayın
- API anahtarlarını environment variables'da saklayın
- HTTPS kullanın
- GDPR/KVKK uyumluluğunu sağlayın

## 📝 Lisans

Bu proje Figma Make platformu üzerinde oluşturulmuştur.

---

**Geliştirici Notu**: Bu sistem, toplantı yönetimi ve ekip performans takibi için kapsamlı bir framework sunar. Gerçek production kullanımı için backend entegrasyonu ve güvenlik önlemleri eklenmelidir.
