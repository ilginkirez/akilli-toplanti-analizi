# MeetingAI - Kurulum ve Geliştirme Kılavuzu

## 🎯 Hızlı Başlangıç

### Sistem Gereksinimleri
- Node.js 18+ 
- npm veya pnpm
- Modern web browser (Chrome, Firefox, Safari, Edge)

### Mevcut Durum
Bu proje şu anda **frontend-only** bir demo olarak çalışmaktadır. Tüm veriler `src/app/data/mockData.ts` dosyasındaki mock verilerden gelmektedir.

## 📁 Proje Yapısı

```
src/
├── app/
│   ├── components/
│   │   ├── Layout.tsx              # Ana layout ve navigasyon
│   │   ├── LoadingSpinner.tsx      # Yükleme göstergesi
│   │   └── ui/                     # Radix UI bileşenleri
│   ├── pages/
│   │   ├── Dashboard.tsx           # Ana dashboard
│   │   ├── Meetings.tsx            # Toplantı listesi
│   │   ├── MeetingDetail.tsx       # Toplantı detayı ve AI analizi
│   │   ├── CreateMeeting.tsx       # Yeni toplantı oluşturma
│   │   ├── Tasks.tsx               # Görev yönetimi (Kanban)
│   │   ├── Analytics.tsx           # Performans analitikleri
│   │   └── NotFound.tsx            # 404 sayfası
│   ├── data/
│   │   └── mockData.ts             # Mock veriler
│   ├── types/
│   │   └── index.ts                # TypeScript type definitions
│   ├── utils/
│   │   ├── helpers.ts              # Yardımcı fonksiyonlar
│   │   └── aiHelpers.ts            # AI entegrasyon helpers (placeholder)
│   ├── routes.tsx                  # Route yapılandırması
│   └── App.tsx                     # Ana uygulama
└── styles/
    ├── fonts.css                   # Font imports
    ├── theme.css                   # Tema değişkenleri
    ├── custom.css                  # Custom styles
    └── index.css                   # Ana CSS dosyası
```

## 🚀 Özellikler

### Tamamlanmış
- ✅ Multi-page routing (React Router v7)
- ✅ Dark/Light mode toggle
- ✅ Dashboard with metrics
- ✅ Meeting management (list, create, detail)
- ✅ AI-powered meeting analysis (mock)
- ✅ Drag & drop task management (Kanban)
- ✅ Performance analytics
- ✅ Responsive design
- ✅ Turkish localization (date-fns)
- ✅ Premium UI/UX design

### Mock Features (Backend Gerektirir)
- 🔄 Video conferencing
- 🔄 Real-time transcription
- 🔄 AI summary generation
- 🔄 Task auto-assignment
- 🔄 Email notifications
- 🔄 Calendar sync

## 🔧 Geliştirme

### Mock Data Düzenleme

Yeni toplantılar, görevler veya kullanıcılar eklemek için:

```typescript
// src/app/data/mockData.ts

export const mockUsers: User[] = [
  // Yeni kullanıcı ekle
  {
    id: '7',
    name: 'Yeni Kullanıcı',
    email: 'yeni@company.com',
    avatar: 'https://i.pravatar.cc/150?img=50',
    role: 'member',
    department: 'Geliştirme'
  },
  // ...
];
```

### Yeni Sayfa Ekleme

1. Yeni component oluştur: `src/app/pages/YeniSayfa.tsx`
2. Route ekle: `src/app/routes.tsx`

```typescript
import { YeniSayfa } from './pages/YeniSayfa';

export const router = createBrowserRouter([
  {
    path: '/',
    Component: Layout,
    children: [
      // ... mevcut routes
      { path: 'yeni-sayfa', Component: YeniSayfa }
    ]
  }
]);
```

3. Navigation ekle: `src/app/components/Layout.tsx`

```typescript
const navigation = [
  // ... mevcut items
  { name: 'Yeni Sayfa', href: '/yeni-sayfa', icon: YourIcon }
];
```

## 🎨 Tema Özelleştirme

### Renkler
`src/styles/theme.css` dosyasını düzenleyin:

```css
:root {
  --color-primary: #your-color;
  /* ... */
}
```

### Fontlar
`src/styles/fonts.css` dosyasına yeni font ekleyin:

```css
@import url('https://fonts.googleapis.com/css2?family=YourFont:wght@400;600;700&display=swap');

* {
  font-family: 'YourFont', sans-serif;
}
```

## 📊 Analytics Metrikleri

### Kişisel Metrikler
- Tamamlanan görevler
- Tamamlanma oranı
- Toplantı katılımı
- Performans skoru
- İş yükü durumu

### Ekip Metrikleri
- Toplam toplantılar
- Tamamlanan görevler
- Gecikmiş görevler
- Ekip performans skoru
- Darboğazlar ve uyarılar
- En iyi performans gösterenler

## 🔐 Backend Entegrasyonu

### 1. Supabase Kurulumu

```bash
npm install @supabase/supabase-js
```

```typescript
// src/lib/supabase.ts
import { createClient } from '@supabase/supabase-js';

export const supabase = createClient(
  process.env.VITE_SUPABASE_URL!,
  process.env.VITE_SUPABASE_ANON_KEY!
);
```

### 2. Authentication

```typescript
// Login
const { data, error } = await supabase.auth.signInWithPassword({
  email: 'user@example.com',
  password: 'password'
});

// Logout
await supabase.auth.signOut();

// Get current user
const { data: { user } } = await supabase.auth.getUser();
```

### 3. Data Fetching

```typescript
// Get meetings
const { data: meetings, error } = await supabase
  .from('meetings')
  .select('*')
  .order('start_time', { ascending: false });

// Create meeting
const { data, error } = await supabase
  .from('meetings')
  .insert([
    { title: 'New Meeting', start_time: '2024-01-01T10:00:00' }
  ]);

// Update task status
const { data, error } = await supabase
  .from('tasks')
  .update({ status: 'completed' })
  .eq('id', taskId);
```

### 4. Real-time Subscriptions

```typescript
// Subscribe to meeting changes
supabase
  .channel('meetings')
  .on('postgres_changes', 
    { event: '*', schema: 'public', table: 'meetings' },
    (payload) => {
      console.log('Change received!', payload);
      // Update UI
    }
  )
  .subscribe();
```

## 🤖 AI Entegrasyonu

### OpenAI API Kullanımı

```typescript
// src/lib/openai.ts
import OpenAI from 'openai';

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// Meeting summary
export async function generateSummary(transcript: string) {
  const response = await openai.chat.completions.create({
    model: "gpt-4-turbo-preview",
    messages: [
      {
        role: "system",
        content: "Toplantı transkriptini Türkçe olarak özetle."
      },
      { role: "user", content: transcript }
    ],
  });
  
  return response.choices[0].message.content;
}

// Task extraction
export async function extractTasks(transcript: string) {
  const response = await openai.chat.completions.create({
    model: "gpt-4-turbo-preview",
    messages: [
      {
        role: "system",
        content: `Transkriptten görevleri çıkar ve JSON formatında döndür:
        { "tasks": [{ "title": "", "assignee": "", "dueDate": "", "priority": "" }] }`
      },
      { role: "user", content: transcript }
    ],
    response_format: { type: "json_object" }
  });
  
  return JSON.parse(response.choices[0].message.content || '{}');
}
```

## 📱 Responsive Design

Uygulama tüm ekran boyutları için optimize edilmiştir:

- **Mobile**: < 768px
- **Tablet**: 768px - 1024px
- **Desktop**: > 1024px

Tailwind breakpoints:
- `sm:` → 640px
- `md:` → 768px
- `lg:` → 1024px
- `xl:` → 1280px
- `2xl:` → 1536px

## 🧪 Testing (Önerilen)

### Unit Tests

```bash
npm install -D vitest @testing-library/react @testing-library/jest-dom
```

```typescript
// src/app/pages/__tests__/Dashboard.test.tsx
import { render, screen } from '@testing-library/react';
import { Dashboard } from '../Dashboard';

describe('Dashboard', () => {
  it('renders upcoming meetings section', () => {
    render(<Dashboard />);
    expect(screen.getByText(/Yaklaşan Toplantılar/i)).toBeInTheDocument();
  });
});
```

### E2E Tests

```bash
npm install -D @playwright/test
```

```typescript
// tests/e2e/meetings.spec.ts
import { test, expect } from '@playwright/test';

test('create new meeting', async ({ page }) => {
  await page.goto('/meetings/new');
  
  await page.fill('#title', 'Test Meeting');
  await page.fill('#date', '2024-12-31');
  await page.fill('#startTime', '10:00');
  
  await page.click('button[type="submit"]');
  
  await expect(page).toHaveURL(/\/meetings$/);
});
```

## 🐛 Debugging

### React DevTools
Chrome extension ile component tree'yi inceleyin

### Network Tab
API çağrılarını monitor edin

### Console Logs
`src/app/utils/aiHelpers.ts` dosyasında AI placeholder fonksiyonları console.log yapar

## 📦 Build & Deploy

### Production Build

```bash
npm run build
```

Build output: `dist/` klasörü

### Environment Variables

`.env` dosyası oluşturun:

```env
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_ANON_KEY=your_anon_key
OPENAI_API_KEY=your_openai_key
LIVEKIT_URL=your_livekit_url
```

### Vercel Deploy

```bash
npm install -g vercel
vercel --prod
```

## 🆘 Sorun Giderme

### Dark mode çalışmıyor
- `ThemeProvider` eklendiğinden emin olun
- `next-themes` package'ı yüklü olmalı

### Routes çalışmıyor
- `RouterProvider` ve `createBrowserRouter` kullanıldığından emin olun
- Route paths doğru olmalı

### Drag & drop çalışmıyor
- `react-dnd` ve `react-dnd-html5-backend` yüklü olmalı
- `DndProvider` component'i sarmalıyor olmalı

## 📚 Kaynaklar

- [React Router Docs](https://reactrouter.com)
- [Tailwind CSS Docs](https://tailwindcss.com)
- [Recharts Docs](https://recharts.org)
- [Radix UI Docs](https://www.radix-ui.com)
- [date-fns Docs](https://date-fns.org)

## 💡 İpuçları

1. **Mock Data**: Production'a geçmeden önce tüm mock data'yı backend ile değiştirin
2. **Error Handling**: API çağrılarına error handling ekleyin
3. **Loading States**: Async işlemler için loading göstergeleri ekleyin
4. **Optimistic Updates**: UI'da hızlı feedback için optimistic updates kullanın
5. **Caching**: React Query veya SWR ile data caching düşünün

---

**Yardıma ihtiyacınız olursa**: Issue açın veya dokümantasyona göz atın!
