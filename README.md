# Akıllı Toplantı Analiz Sistemi

Bu proje, çok katılımcılı çevrimiçi toplantıları gerçek zamanlı olarak izleyen, konuşmacıları kanal bazlı ayrıştıran ve toplantı sonunda RTTM ile JSON raporları üreten uçtan uca bir platformdur.

## Proje Yapısı

- `frontend/`: React + Vite tabanlı toplantı arayüzü.
- `meeting_analyzer/`: FastAPI backend, Celery işleri, VAD akışı ve testler.
- `meeting_analyzer/src/storage/`: oturum metaverisi, `session.json` ve `events.jsonl` çıktıları.
- `meeting_analyzer/recordings/`: ses / video kayıtları ve analiz çıktıları.
- `meeting_analyzer/cdr/`: OpenVidu CDR logları.
- `docker-compose.yml`: Redis, OpenVidu, backend, worker ve frontend servisleri.
- `start-remote-test.ps1` ve `stop-remote-test.ps1`: yerel uzaktan test akışı.

## Temiz Yapı Notları

- Root seviyedeki eski `src/` ve `recordings/` klasörleri artık kullanılmıyor.
- Backend giriş noktası çalışma dizinini otomatik olarak `meeting_analyzer/` içine alır, böylece göreli yollar tek yerde toplanır.
- Yerel ortam dosyası için `compose.env` yerine `compose.env.example` kullanın.
- Frontend tarafında örnek üretim değişkeni için `frontend/env.production.example` dosyası vardır.

## Hızlı Başlangıç

1. Frontend bağımlılıklarını kurun:

   ```powershell
   cd frontend
   npm install
   ```

2. Backend bağımlılıklarını kurun:

   ```powershell
   cd meeting_analyzer
   pip install -r requirements.txt
   pip install -r requirements_async.txt
   ```

3. Tüm sistemi başlatın:

   ```powershell
   .\start-remote-test.ps1
   ```

## Manuel Çalıştırma

Sadece backend'i ayağa kaldırmak isterseniz:

```powershell
cd meeting_analyzer
python main.py --host 0.0.0.0 --port 8000
```

## Uzaktan Test

Uzak cihazlardan erişim için `start-remote-test.ps1` betiği frontend'i açar, ngrok tünelini kurar ve backend ile OpenVidu'yu Docker Compose ile başlatır.

İpuçları:

- Mikrofon izni için erişimi `https://` üzerinden açın.
- Gerekirse ngrok sürecini `taskkill /f /im ngrok.exe` ile kapatın.
- Sorun giderirken loglar geçici olarak Windows `%TEMP%` klasörü altına yazılır.

## Geliştirme Notları

- OpenVidu sürümü `2.30.0` ile sabitlenmiştir.
- Backend çıktılarını temiz tutmak için cache, log ve paket klasörleri `.gitignore` ile dışlanmıştır.
- Yeni bir ortam kurarken `compose.env.example` ve `frontend/env.production.example` dosyalarını başlangıç şablonu olarak kullanın.

