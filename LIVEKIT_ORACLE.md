# LiveKit Oracle Deployment ve Migration Notlari

Bu dalda uygulama, OpenVidu/Kurento akisindan cikartilip LiveKit self-hosted
akisine tasindi. Hedef mimari:

- Oracle Cloud ARM VM
- Ubuntu 22.04 / 24.04
- Docker Compose
- Caddy ile HTTPS / WSS
- LiveKit SFU
- Coturn ile TURN UDP/TCP fallback

## Mimari

```text
Browser
  -> https://APP_DOMAIN        -> Caddy -> frontend + /api -> backend
  -> wss://RTC_DOMAIN          -> Caddy -> livekit:7880
  -> tcp://VM:7881            -> LiveKit ICE/TCP fallback
  -> udp://VM:50000-50100     -> LiveKit RTP/ICE UDP
  -> udp/tcp://TURN_DOMAIN:3478 -> Coturn relay/fallback
  -> udp/tcp://VM:51000-51100 -> Coturn relay port range
```

## Repodaki ilgili dosyalar

- `docker-compose.oracle.yml`
- `compose.oracle.env.example`
- `livekit/livekit.yaml.example`
- `Caddyfile.oracle`
- `meeting_analyzer/src/services/livekit_service.py`
- `meeting_analyzer/src/routers/livekit.py`
- `meeting_analyzer/src/routers/sessions.py`
- `frontend/src/app/hooks/useMeeting.ts`

## 1. Oracle tarafi

### DNS / host isimleri

Gercek domain yoksa sslip.io kullanabilirsiniz:

- `APP_DOMAIN=79-76-123-190.sslip.io`
- `RTC_DOMAIN=rtc.79-76-123-190.sslip.io`
- `TURN_DOMAIN=turn.79-76-123-190.sslip.io`

`APP_DOMAIN`, `RTC_DOMAIN`, `TURN_DOMAIN` hepsi ayni Oracle public IP'ye
cozulmeli.

### Security List / NSG Ingress

Acmaniz gereken portlar:

- TCP `22`
- TCP `80`
- TCP `443`
- TCP `7881`
- TCP `3478`
- UDP `3478`
- UDP `50000-50100`
- TCP `51000-51100`
- UDP `51000-51100`

Not:

- `443` sadece uygulama ve LiveKit signaling icin.
- Medya akisi `50000-50100/udp`.
- TURN relay icin `51000-51100` ayrildi.

## 2. Ubuntu iptables

Kalici policy baska bir arac ile yonetilmiyorsa asagidaki kurallar yeterli:

```bash
sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT
sudo iptables -I INPUT -p tcp --dport 7881 -j ACCEPT
sudo iptables -I INPUT -p tcp --dport 3478 -j ACCEPT
sudo iptables -I INPUT -p udp --dport 3478 -j ACCEPT
sudo iptables -I INPUT -p udp --dport 50000:50100 -j ACCEPT
sudo iptables -I INPUT -p tcp --dport 51000:51100 -j ACCEPT
sudo iptables -I INPUT -p udp --dport 51000:51100 -j ACCEPT
sudo netfilter-persistent save
```

Kontrol:

```bash
sudo ss -lntup | grep -E '(:80|:443|:7881|:3478|:50000|:50100|:51000|:51100)'
```

## 3. Docker Compose calistirma

Sunucuda:

```bash
cd ~/akilli-toplanti-analizi
cp compose.oracle.env.example compose.oracle.env
nano compose.oracle.env
docker compose --env-file compose.oracle.env -f docker-compose.oracle.yml up -d --build
docker compose --env-file compose.oracle.env -f docker-compose.oracle.yml ps
docker compose --env-file compose.oracle.env -f docker-compose.oracle.yml logs -f livekit coturn gateway backend
```

## 4. Backend migration ozeti

Mevcut `/api/sessions/token` endpoint'i korunuyor ama artik OpenVidu token
degil LiveKit token donuyor.

Yeni aktif servis:

- `meeting_analyzer/src/services/livekit_service.py`

Canli endpointler:

- `POST /api/sessions/token`
- `GET /api/sessions`
- `POST /api/sessions`
- `POST /api/sessions/{session_id}/stop`
- `GET /api/livekit/rooms`
- `POST /api/livekit/rooms`
- `DELETE /api/livekit/rooms/{room_name}`
- `GET /api/livekit/rooms/{room_name}/participants`
- `POST /api/livekit/webhook`

### Once: OpenVidu / manuel baglanti tokeni

```python
token_or_connection = await openvidu_service.create_token(session_id, participant_id)
await session.connect(response.token, clientData)
```

### Sonra: LiveKit token

```python
await livekit_service.create_room(room_name=session_id)

token = livekit_service.create_access_token(
    room_name=session_id,
    participant_id=participant_id,
    display_name=display_name,
    metadata=server_data,
)
```

### Room yonetimi

```python
await livekit_service.create_room("toplanti-123")
await livekit_service.list_rooms()
await livekit_service.list_participants("toplanti-123")
await livekit_service.delete_room("toplanti-123")
```

### Webhook

LiveKit webhook endpoint'i:

- `POST /api/livekit/webhook`

Bu endpoint:

- `room_started`
- `participant_joined`
- `participant_left`
- `participant_connection_aborted`
- `track_published`
- `room_finished`

olaylarini alip session store'u gunceller.

## 5. Frontend migration ozeti

Mevcut `RTCPeerConnection` / OpenVidu session akisi yerine `livekit-client`
kullaniliyor.

Ana dosya:

- `frontend/src/app/hooks/useMeeting.ts`

### Once: ham / OpenVidu akisi

```ts
const pc = new RTCPeerConnection({ iceServers });
pc.onicecandidate = ({ candidate }) => ws.send(JSON.stringify({ candidate }));
pc.oniceconnectionstatechange = () => {
  if (pc.iceConnectionState === 'disconnected') {
    pc.restartIce();
  }
};
```

### Sonra: LiveKit akisi

```ts
const room = new Room({
  adaptiveStream: true,
  dynacast: true,
  videoCaptureDefaults: {
    resolution: VideoPresets.h720.resolution,
  },
});

room.on(RoomEvent.Reconnecting, () => {
  console.log('media reconnecting');
});

room.on(RoomEvent.Reconnected, () => {
  console.log('media restored');
});

await room.connect(wsUrl, token);
await room.localParticipant.setMicrophoneEnabled(true);
await room.localParticipant.setCameraEnabled(true);
```

### Kamera / mikrofon

Once:

```ts
const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: true });
stream.getTracks().forEach((track) => pc.addTrack(track, stream));
```

Sonra:

```ts
await room.localParticipant.setMicrophoneEnabled(true);
await room.localParticipant.setCameraEnabled(true);
```

### Uzak katilimcilari dinleme

Once:

```ts
pc.ontrack = (event) => {
  remoteVideo.srcObject = event.streams[0];
};
```

Sonra:

```ts
room.on(RoomEvent.TrackSubscribed, () => {
  syncRoomState(room);
});
```

Not:

- `syncRoomState()` remote participant track publication'larindan `MediaStream`
  olusturur.
- `VideoParticipant` bileşeni artik gizli bir `audio` elementi ile ses akisini
  de oynatir.

## 6. ICE ve reconnect farki

### Ham WebRTC

- ICE candidate toplama sizin sorumlulugunuzdaydi.
- Offer/answer candidate exchange sizin signaling sunucunuzdaydi.
- Kopunca `restartIce()` ve yeni `offer({ iceRestart: true })` mantigi size aitti.

### LiveKit

- Signaling kanali ve participant state server tarafinda yonetilir.
- ICE/UDP -> TURN/UDP -> ICE/TCP fallback stratejisi istemci SDK + server
  tarafinda otomatik isler.
- Ag degisimlerinde SDK websocket'i tekrar baglar ve ICE restart'i kendi tetikler.

## 7. Test ve dogrulama

### Backend

```bash
curl https://APP_DOMAIN/api/health
curl https://APP_DOMAIN/api/livekit/rooms
```

Beklenen:

- `rtc_provider: "livekit"`
- `livekit_connected: true`

### Browser

Iki ayri cihaz veya gizli pencere ile:

1. `https://APP_DOMAIN`
2. Ayni `sessionId` ile iki farkli katilimci girisi
3. Kamera + mikrofon yayin kontrolu
4. Bir istemcide Wi-Fi kapat/ac veya VPN ac/kapat
5. UI'da `Baglanti yeniden kuruluyor...` gorunup sonra toparlamasi

### Sunucu loglari

```bash
docker compose --env-file compose.oracle.env -f docker-compose.oracle.yml logs -f livekit coturn backend gateway
```

Bakilacak noktalar:

- `gateway` sertifika almis mi
- `livekit` hata vermeden 7880/7881 dinliyor mu
- `coturn` 3478 ve relay range ile ayaga kalkmis mi
- `backend` webhook aliyor mu

## 8. Yaygin hatalar

### `ICE failed` veya `reconnecting` uzun suruyor

Kontrol et:

- Oracle Security List UDP range acik mi
- Ubuntu iptables UDP `50000-50100` acik mi
- `PUBLIC_IP` dogru mu
- `TURN_DOMAIN` public IP'ye cozuluyor mu

### `401 webhook verification failed`

- `LIVEKIT_API_KEY` backend ile livekit config'te ayni olmali
- `LIVEKIT_API_SECRET` backend ile livekit config'te ayni olmali

### `RoomEvent.Disconnected` hemen geliyor

- `LIVEKIT_WS_URL` yanlis olabilir
- `RTC_DOMAIN` sertifikasi alinmamis olabilir
- `RTC_DOMAIN` DNS'i Oracle IP'ye cozunmuyor olabilir

### Ses var goruntu yok

- UDP `50000-50100` acik degilse en yaygin belirti budur
- TCP `7881` sadece fallback'tir, UDP kapaliysa kalite ciddi duser

## 9. Bilinen sinir

Bu migration kayit tarafini kapatmiyor ama aktif egress de kurmuyor.
Su an recording endpoint'leri kontrollu sekilde `disabled` donuyor.

Eger ikinci fazda kayit istenirse:

- LiveKit Egress container
- object storage / local storage
- webhook ile `egress_started`, `egress_updated`, `egress_ended`

eklenmeli.
