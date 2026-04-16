# Akilli Toplanti Analiz Sistemi

Bu proje, cok katilimcili cevrimici toplantilari gercek zamanli olarak yoneten, katilimci bazli ses kaydi alabilen ve toplanti sonunda konusmaci zaman cizelgesi uretebilen uctan uca bir platformdur.

Guncel mimari `LiveKit + Coturn + FastAPI + React` uzerine kuruludur.

## Proje Yapisi

- `frontend/`: React + Vite tabanli toplanti arayuzu
- `meeting_analyzer/`: FastAPI backend, kayit akisi, analiz servisi ve testler
- `meeting_analyzer/src/storage/`: oturum metadata dosyalari
- `meeting_analyzer/recordings/`: participant bazli ses kayitlari ve analiz ciktilari
- `docker-compose.oracle.yml`: Oracle Ubuntu uzerindeki canli servis orkestrasyonu
- `compose.oracle.env.example`: Oracle dagitimi icin ornek env dosyasi
- `LIVEKIT_ORACLE.md`: LiveKit/Oracle kurulum notlari

## Guncel Mimari

Bu sistem saf peer-to-peer degildir. `LiveKit SFU` tabanli sunucu destekli WebRTC kullanir.

Ana bilesenler:

- `frontend`: `livekit-client` ile odaya baglanir
- `backend`: LiveKit token uretir, participant ve kayit metadata'sini tutar
- `livekit`: medya yonlendirme katmani
- `coturn`: TURN/STUN destegi
- `gateway`: Caddy ile HTTPS ve reverse proxy

## Hizli Baslangic

1. Frontend bagimliliklarini kurun:

```powershell
cd frontend
npm install
```

2. Backend bagimliliklarini kurun:

```powershell
cd meeting_analyzer
pip install -r requirements.txt
pip install -r requirements_async.txt
```

3. Yerel gelistirme icin backend'i calistirin:

```powershell
cd meeting_analyzer
python main.py --host 0.0.0.0 --port 8000
```

## Oracle Ubuntu VM'e Degisiklik Yansitma

Yerelde frontend veya backend tarafinda yaptigin degisiklikler Ubuntu sunucuya otomatik gitmez. Dogru akis su sekildedir:

### 1. Yerelde commit ve push yap

```powershell
cd "C:\Users\HP\Desktop\akilli-toplanti-analizi"
git status
git add .
git commit -m "feat(frontend): arayuz guncellemeleri"
git push akilli-toplanti-analizi master
```

### 2. Windows PowerShell'den Oracle Ubuntu VM'e baglan

```powershell
ssh -i "C:\Users\HP\Downloads\ssh-key-2026-04-15.key" ubuntu@79.76.123.190
```

Su prompt'u goruyorsan dogru yerdesin:

```bash
ubuntu@instance-20260415-1214:~$
```

### 3. VM icinde repoyu guncelle

```bash
cd ~/akilli-toplanti-analizi
git remote -v
git pull --ff-only origin master || git pull --ff-only akilli-toplanti-analizi master
```

### 4. Docker stack'i yeniden build et ve ayaga kaldir

```bash
docker compose --env-file compose.oracle.env -f docker-compose.oracle.yml up -d --build
docker compose --env-file compose.oracle.env -f docker-compose.oracle.yml ps
docker compose --env-file compose.oracle.env -f docker-compose.oracle.yml logs --tail 120 gateway backend
```

## Onemli Notlar

- `git pull` ve `docker compose` komutlari Windows'ta degil, Ubuntu VM icinde calistirilmalidir.
- `compose.oracle.env` dosyasi proje klasoru icinde bulunmalidir.
- Windows tarafinda `Docker Desktop` kapaliysa yerel `docker compose` komutlari calismaz.
- Sunucuda remote adi `origin` degilse ikinci `git pull` alternatifi kullanilabilir.

## Kayitlar Nereye Yazilir

Canli sunucuda participant bazli kayitlar ve analiz ciktilari su klasore yazilir:

```bash
/home/ubuntu/akilli-toplanti-analizi/meeting_analyzer/recordings
```

Ornek yapi:

```text
recordings/toplanti1/individual/par_xxxxxx-20260416T124603.webm
recordings/toplanti1/individual/par_yyyyyy-20260416T124622.webm
recordings/toplanti1/analysis/speech_segments.json
recordings/toplanti1/analysis/speakers.rttm
```

## Toplanti Analizi Ciktilari

Guncel akista:

- her katilimcinin mikrofonu ayri kaydedilir
- kayitlar backend'e yuklenir
- analiz servisi `speech_segments.json` uretir
- `speakers.rttm` dosyasi olusturulur

Bu sayede:

- kim hangi saniyede konustu
- hangi participant ne kadar konustu
- overlap olan bolgeler

gibi bilgiler cikartilabilir.

## Ilgili Dokumanlar

- `LIVEKIT_ORACLE.md`
