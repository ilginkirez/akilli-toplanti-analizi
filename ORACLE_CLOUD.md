# Oracle Cloud Kurulumu

Bu repo icin Oracle Cloud yolu su sekilde calisir:

- `gateway` uzerinden frontend ve backend tek domain/tek IP altinda servis edilir.
- `openvidu` konteyneri ic agda calisir.
- Caddy, `/api` istegini backend'e, `/openvidu` istegini OpenVidu'ya yollar.
- WebRTC medya trafigi icin `3478` ile Kurento medya port araligi Oracle tarafinda acilir.

Bu kurulumdaki komutlar Oracle VM uzerinde calistirilmalidir. Yerel Windows Docker'inda `80` portu doluysa bu normaldir; o ortamda deneme yapmak bu akisin amaci degil.

## Bu kurulum neyi cozer?

Arkadasinla ayni linkten baglanabiliyor ama ses/goruntu gelmiyorsa sebep genelde sunlardan biridir:

- HTTPS yoktur.
- OpenVidu token'i yanlis public adresi ilan ediyordur.
- WebRTC portlari firewall / security list tarafinda kapali kalmistir.

Bu kurgu bunlari duzeltmek icin hazirlandi.

Not: Oracle compose'ta Kurento konfigurasyon dosyasini container icine `read-only` mount etmeyin.
OpenVidu baslangicta bu dosyayi guncellemeye calisir; `:ro` kullanilirsa `kms` kalkmaz ve
`KMS ... is not reachable` hatasi alirsiniz.

## Gerekli portlar

Oracle Cloud Security List veya NSG tarafinda su portlari acin:

- `80/tcp`
- `443/tcp`
- `3478/tcp`
- `3478/udp`
- `42000-42100/tcp`
- `42000-42100/udp`

## Ortam dosyasi

Kullanim icin su dosyayi temel alin:

- `compose.oracle.env.example`

Icindeki degerler:

- `DOMAIN_OR_PUBLIC_IP=92.5.71.75`
- `COTURN_IP=92.5.71.75`
- `HTTPS_PORT=443`
- `GATEWAY_HTTP_PORT=80`
- `GATEWAY_HTTPS_PORT=443`
- `OPENVIDU_URL=http://openvidu:443`
- `OPENVIDU_WEBHOOK_ENDPOINT=http://backend:8000/api/openvidu/webhook`
- `KMS_MIN_PORT=42000`
- `KMS_MAX_PORT=42100`

Eger sadece IP kullaniyorsaniz, Caddy `tls internal` ile calisir. Bu durumda ilk giriste browser sertifika uyari verebilir. `Advanced` -> `Continue` ile ilerleyebilirsiniz.

## Calistirma

Sunucuda:

```bash
chmod +x deploy-oracle.sh
./deploy-oracle.sh
```

## Acilacak link

Ortam ayaga kalkinca uygulamayi su adresten acin:

`https://<public-ip>/`

Yerel Windows denemesi gerekiyorsa `compose.local.env.example` kullanin ve `https://localhost:8443/` ile acin.

## Notlar

- `/api/*` istekleri backend'e gider.
- `/openvidu*` istekleri OpenVidu server'a gider.
- Backend, OpenVidu ile Docker agi icinden `http://openvidu:443` uzerinden konusur.
- TURN/STUN icin tarayici ayni public host uzerinden `3478` portuna baglanir.
- Oracle gibi public IP'si NAT arkasinda gorunen ortamlarda `COTURN_IP` degerini public IPv4 olarak acikca verin.
- Eger domain eklerseniz, `tls internal` yerine gercek TLS sertifikasi kullanmak daha temiz olur.

## Sorun olursa

Kontrol icin:

```bash
docker compose -f docker-compose.oracle.yml ps
docker compose -f docker-compose.oracle.yml logs -f gateway
docker compose -f docker-compose.oracle.yml logs -f backend
docker compose -f docker-compose.oracle.yml logs -f openvidu
```
