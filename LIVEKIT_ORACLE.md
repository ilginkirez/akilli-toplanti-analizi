# LiveKit Oracle Deployment Notlari

Bu proje Oracle Ubuntu uzerinde `LiveKit + Coturn + FastAPI + React` mimarisiyle
calisir.

## Mimari

- `gateway`: HTTPS ve reverse proxy
- `backend`: token, session metadata ve kayit yukleme
- `livekit`: SFU ve signaling
- `coturn`: TURN/STUN fallback
- `redis`, `celery_worker`, `celery_beat`: arka plan isleri

## Gerekli dosyalar

- `docker-compose.oracle.yml`
- `compose.oracle.env`
- `Caddyfile.oracle`
- `meeting_analyzer/src/services/livekit_service.py`
- `frontend/src/app/hooks/useMeeting.ts`

## Oracle ag portlari

- TCP `22`
- TCP `80`
- TCP `443`
- TCP `7881`
- TCP `3478`
- UDP `3478`
- UDP `50000-50100`
- TCP `51000-51100`
- UDP `51000-51100`

## Kurulum

```bash
cd ~/akilli-toplanti-analizi
cp compose.oracle.env.example compose.oracle.env
nano compose.oracle.env
docker compose --env-file compose.oracle.env -f docker-compose.oracle.yml up -d --build
docker compose --env-file compose.oracle.env -f docker-compose.oracle.yml ps
docker compose --env-file compose.oracle.env -f docker-compose.oracle.yml logs -f livekit coturn gateway backend
```

## Beklenen health sonucu

```bash
curl https://APP_DOMAIN/api/health
```

Beklenen alanlar:

- `status: "ok"`
- `rtc_provider: "livekit"`
- `livekit_connected: true`

## Not

- Medya signaling `wss://RTC_DOMAIN` uzerinden gider.
- UDP `50000-50100` kapaliysa goruntu ve ses kalitesi hizla bozulur.
- TURN icin `TURN_DOMAIN` public IP'ye cozulmelidir.
