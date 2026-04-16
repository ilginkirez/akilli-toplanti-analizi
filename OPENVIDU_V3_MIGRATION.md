# OpenVidu 3 / LiveKit Gecis Notlari

Bu proje, Kurento tabanli OpenVidu 2.30.0 kurulumundan daha saglam bir medya katmani elde etmek icin
OpenVidu 3 tarafina gecise hazirlanmistir.

## Bu repoda yapilanlar

- Frontend `openvidu-browser` yerine `openvidu-browser-v2compatibility` kullanir.
- Backend mevcut `/openvidu/api/*` oturum ve token akisini korur.
- Kod tabani, OpenVidu 2.x API semantigini koruyarak OpenVidu 3'teki uyumluluk katmanina hazir hale getirilmistir.

## Kritik not

OpenVidu 3 uzerinde eski OpenVidu Browser / REST akisini korumak icin `v2compatibility` modulu gerekir.
Bu modul resmi OpenVidu dagitiminda ticari ozellik olarak sunulabilir. Kurulum yapmadan once lisans ve
surum uygunlugunu resmi dokumandan dogrulayin.

## Sunucu tarafinda beklenen hedef durum

- OpenVidu 3 deployment kullanin.
- `v2compatibility` modulu acik olsun.
- Uygulama backend'i `OPENVIDU_URL` degiskeni ile bu deployment'in public URL'ine baglansin.
- `OPENVIDU_SECRET` degeri deployment ile ayni olsun.

Ornek:

```env
OPENVIDU_URL=https://video.example.com
OPENVIDU_SECRET=CHANGE_ME
SSL_VERIFY=true
```

## Beklenen kazanimlar

- Kurento / KMS baslatma sorunlarindan cikis
- Daha saglam NAT ve ICE davranisi
- Daha modern medya katmani
- OpenVidu 2 tarzi istemci akisini tamamen cope atmadan gecis yapabilme

## Ne degismedi

- Backend token/session endpointleri korunur.
- Frontend toplantiya katilma akisi ayni kalir.
- Katilimci kaydi, stream kaydi ve backend metaveri akislari korunur.

## Sonraki adim

Uzun vadede daha fazla esneklik ve daha az vendor bagimliligi istenirse,
uygulama `livekit-client` ve dogrudan LiveKit token uretimine tamamen tasinabilir.
Bu ise ayri bir tam gecis calismasidir.
