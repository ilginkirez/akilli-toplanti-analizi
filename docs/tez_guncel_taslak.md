# Akıllı Toplantı Analizi Tezi İçin Güncel Revizyon Taslağı

Bu dosya, mevcut tez iskeletini koruyup yalnızca güncel mimariyle çelişen kısımları düzeltmek, eksik kalan yeni katmanları eklemek ve mevcut kaynak havuzunu koruyarak metni güçlendirmek amacıyla hazırlanmıştır. Amaç tezi baştan yazmak değil, çalışan sistemi akademik olarak daha doğru ve daha güçlü anlatmaktır.

Bu taslak hazırlanırken üç ilke izlendi:

1. Mevcut tez omurgası ve bölüm mantığı mümkün olduğunca korundu.
2. Kodda gerçekten bulunan bileşenler ana katkı olarak güçlendirildi.
3. Çelişen kısımlar nokta atışı düzeltildi; mevcut kaynak havuzu silinmek yerine korunacak biçimde yeniden sınıflandırıldı.

Not: Bulgular bölümünde sayısal performans değerleri uydurulmamıştır. O bölüm için doldurulabilir ama akademik olarak güvenli bir yazım iskeleti verilmiştir.

## 1. Korunacak Omurga ve Güncellenecek Noktalar

| Tezde korunacak eksen | Güncellenecek anlatı | Müdahale biçimi |
| --- | --- | --- |
| Çok ajanlı toplantı analizi yaklaşımı | Ajan katmanının kod karşılığı daha somut verilmeli | LangGraph grafı ve `MeetingState` yapısı açıkça eklenmeli |
| ASR, toplantı özeti ve aksiyon çıkarımı | Görev ayrımı korunmalı, ancak ajan rolleri güncel akışla anlatılmalı | Mevcut bölümler korunup çalışma zamanı ayrıntıları eklenmeli |
| Konuşmacı ayrımı anlatısı | Tek kanallı diarization vurgusu yerine çok kanallı kanal-etkinlik çözümlemesi öne çıkarılmalı | Kavram düzeyinde güncelleme yapılmalı |
| Medya ve kayıt katmanı | Ana yöntem bölümünde LiveKit ve track egress merkezde anlatılmalı | Güncel altyapı ayrıntıları eklenmeli |
| Duygu analizi, RAG, FAISS ve bildirimler | Çekirdek ürün akışında merkezde değiller | İlgili çalışmalar veya gelecek çalışmalar düzeyinde tutulmalı |
| Kaynakça yapısı | Mevcut kaynaklar korunmalı, yeni kaynaklar ek katman olarak eklenmeli | Kaynak havuzu iki parçalı biçimde düzenlenmeli |

## 2. Güncel Tezin Ana Tezi

Bu bitirme çalışması, çevrim içi toplantıların yalnızca görüntülü görüşme düzeyinde yönetilmesini değil, toplantı verisinin katılımcı kimliği korunmuş biçimde toplanmasını, çok kanallı zaman ekseninde çözümlenmesini ve LangGraph tabanlı ajan orkestrasyonu ile anlamsal çıktılara dönüştürülmesini hedefleyen bütünleşik bir toplantı analizi platformu önermektedir. Sistemin özgün yönü, konuşmacı kimliğini büyük ölçüde toplantı sonrası tahmin etmeye çalışan klasik tek kanallı diarization boru hatlarından ayrılarak, katılımcı başına ayrılmış ses kanallarını doğrudan veri edinim mimarisinin içine yerleştirmesidir. Böylece konuşmacı ataması, medya toplama düzeyinden itibaren sistem mimarisinin bir özelliği haline gelmektedir.

Bu mimaride LiveKit, gerçek zamanlı oda yönetimi, katılımcı yetkilendirmesi, olay bildirimi ve track-level medya dışa aktarımı için kullanılmaktadır [1][2][3]. Üretilen ayrı ses kanalları, standartlaştırma, hizalama, enerji tabanlı çok kanallı ses etkinlik tespiti, overlap tespiti ve RTTM üretimi aşamalarından geçirilmekte; ardından LangGraph ile tanımlanmış durum grafı, transkripsiyon, özetleme ve aksiyon çıkarımı görevlerini ortak toplantı durumu üzerinde koordine etmektedir [5][6][13][14]. Böylece sistem, medya düzeyi ile anlamsal analiz düzeyini aynı ürün çatısı altında birleştiren modüler bir araştırma ve uygulama altyapısı sunmaktadır.

## 3. Güncellenmiş Özet Önerisi

### Türkçe Özet

Bu bitirme projesi, uzaktan ve hibrit toplantılarda ortaya çıkan üç temel problemi ele almaktadır: toplantı verisinin güvenilir biçimde toplanamaması, konuşmacı bazlı konuşma akışının yeterince ayrıştırılamaması ve toplantı sonrasında eyleme dönüştürülebilir çıktılar üretilememesi. Bu amaçla çalışmada, LiveKit tabanlı gerçek zamanlı medya altyapısını çok kanallı konuşma analizi ve LangGraph tabanlı ajan orkestrasyonu ile birleştiren uçtan uca bir akıllı toplantı platformu geliştirilmiştir. Sistem, her katılımcının mikrofon akışını ayrı bir iz olarak kaydetmekte, bu izleri ortak zaman ekseninde hizalamakta ve enerji tabanlı çok kanallı ses etkinlik tespiti ile tekil konuşma ve örtüşen konuşma bölgelerini belirlemektedir. Elde edilen segmentler RTTM ve zaman çizelgesi biçiminde saklanmakta; ardından transkripsiyon, özetleme ve aksiyon maddesi çıkarımı görevleri ajan düğümleri halinde koordine edilmektedir. Bu yapı sayesinde toplantı sonunda konuşmacı bazlı süre dağılımı, tam metin transkript, yönetici özeti, karar listesi ve görev adayları üretilebilmektedir. Çalışmanın temel katkısı, konuşmacı kimliğini sonradan tahmin etmeye dayalı klasik diarization anlayışı yerine, konuşmacı ayrımını veri edinim mimarisinin içine yerleştiren ve bunu LangGraph ile yönetilen anlamsal analiz katmanıyla birleştiren bütünleşik bir tasarım önermesidir.

### İngilizce Abstract

This thesis presents an end-to-end smart meeting analysis platform that combines a LiveKit-based realtime media layer with multi-channel speech analysis and LangGraph-based agent orchestration. The system addresses three practical problems of modern online meetings: reliable acquisition of participant-level media, speaker-aware analysis of overlapping conversational flow, and generation of actionable post-meeting outputs. Instead of relying solely on post-hoc single-channel speaker diarization, the proposed architecture captures each participant's microphone stream as a separate track, aligns these tracks on a shared timeline, and applies multi-channel voice activity detection to identify single-speaker and overlapping speech regions. The resulting segments are stored as structured timeline data and RTTM annotations. On top of this speech layer, a LangGraph-based agent workflow coordinates transcription, meeting summarization, and action-item extraction. As a result, the platform can generate participant-level speaking statistics, full transcripts, executive summaries, key decisions, and reviewable action items. The main contribution of the thesis is an integrated architecture in which speaker separation is embedded into the media acquisition pipeline itself and then combined with a graph-based agent layer for higher-level semantic analysis.

## 4. İçindekiler Önerisi

1. Giriş
   1. Problem Tanımı
   2. Çalışmanın Amacı
   3. Kapsam
   4. Katkılar
2. İlgili Çalışmalar
   1. WebRTC, SFU ve toplantı medya altyapıları
   2. ASR ve toplantı transkripsiyonu
   3. Konuşmacı ayrımı, çok kanallı VAD ve overlap modelleme
   4. Toplantı özetleme ve aksiyon maddesi çıkarımı
   5. LangGraph ve ajan orkestrasyonu
3. Yöntem ve Sistem Tasarımı
   1. Genel mimari
   2. LiveKit tabanlı medya edinimi
   3. Oturum durumu ve veri saklama yapıları
   4. Çok kanallı konuşma analizi
   5. LangGraph ajan katmanı
   6. Kullanıcı arayüzü ve raporlama
   7. Dağıtım mimarisi
4. Bulgular ve Değerlendirme
5. Sonuç ve Gelecek Çalışmalar

## 5. Bölüm 1: Giriş

### 5.1 Problem Tanımı

Kurumsal ve akademik toplantılar, karar alma ve koordinasyon süreçlerinin merkezinde yer almakla birlikte, çevrim içi ortama taşındıklarında üç yeni problem daha görünür hale gelmektedir. Birinci problem, toplantı verisinin yapısal olmayan biçimde dağılmasıdır. Görüntü, ses, katılımcı hareketleri, bağlantı olayları ve toplantı sonrası notlar farklı katmanlarda üretildiği için toplantı sonrasında güvenilir bir kurumsal hafıza oluşturmak zorlaşmaktadır. İkinci problem, konuşmacı kimliğinin toplantı sonrasında tahmin edilmeye çalışılmasıdır. Tek kanallı kayıtlar üzerinde çalışan klasik diarization yaklaşımları, özellikle örtüşen konuşmalarda ve mikrofon sızıntısı bulunan durumlarda hataya açıktır [7][8]. Üçüncü problem ise, toplantı sonunda elde edilen çıktıların çoğu zaman pasif bilgi olarak kalmasıdır. Transkript üretimi tek başına yeterli değildir; toplantının özeti, alınan kararlar ve takip edilmesi gereken görevler de otomatik olarak ortaya konmalıdır [9][10][11][12].

Bu çalışmada söz konusu problemler, yalnızca doğal dil işleme tarafından değil, medya altyapısından başlayan uçtan uca bir sistem tasarımıyla ele alınmaktadır. Temel varsayım şudur: konuşmacı ayrımı ne kadar erken, yani veri edinim aşamasında güvence altına alınırsa, takip eden transkripsiyon ve toplantı analizi katmanları o kadar güvenilir çalışır.

### 5.2 Çalışmanın Amacı

Bu çalışmanın amacı, çevrim içi toplantıların gerçek zamanlı olarak yürütülmesini sağlayan, toplantı sırasında üretilen medya akışlarını katılımcı bazında kaydeden, toplantı sonrasında ise çok kanallı analiz ve LangGraph tabanlı ajan orkestrasyonu aracılığıyla yapılandırılmış çıktılar üreten bir platform geliştirmektir. Bu bağlamda amaç yalnızca bir video konferans aracı geliştirmek değildir; amaç, toplantının medya düzeyi ile semantik analiz düzeyi arasında süreklilik kuran araştırma niteliğinde bir ürün mimarisi oluşturmaktır.

### 5.3 Kapsam

Çalışmanın kapsamı aşağıdaki alt sistemleri içermektedir:

- LiveKit tabanlı oda, katılımcı ve token yönetimi
- Katılımcı başına ayrı ses izlerinin elde edilmesi
- Track egress ile sunucu taraflı ses kaydı
- Ses dosyalarının standardizasyonu ve ortak zaman ekseninde hizalanması
- Çok kanallı enerji tabanlı konuşma segmentasyonu
- Overlap bölgelerinin ve konuşmacı zaman çizelgesinin çıkarılması
- RTTM üretimi ve oturum bazlı metriklerin hesaplanması
- LangGraph tabanlı transkripsiyon, özetleme ve aksiyon çıkarımı
- React tabanlı toplantı odası ve toplantı sonrası analiz ekranları

Mevcut kod tabanında doğrulanmayan bazı başlıklar ise kapsam dışında tutulmalıdır. Bunlar arasında tam anlamıyla ürünleşmiş duygu analizi, RAG tabanlı uzun süreli hafıza, FAISS tabanlı bağlamsal arama ve SendGrid tabanlı görev bildirimleri bulunmaktadır. Bu başlıklar istenirse gelecek çalışma olarak anılabilir, ancak ana yöntem ve ana katkı bölümünde merkeze yerleştirilmemelidir.

### 5.4 Çalışmanın Katkıları

Bu tezde vurgulanabilecek başlıca katkılar şunlardır:

1. Konuşmacı ayrımını yalnızca sonradan çözülen bir tahmin problemi olmaktan çıkarıp medya edinim mimarisinin doğal bir özelliği haline getiren bir sistem tasarımı geliştirilmiştir.
2. LiveKit tabanlı gerçek zamanlı oda yönetimi ile track-level kayıt mantığı birleştirilerek katılımcı bazlı ses izleri güvenilir biçimde toplanmıştır [1][2][3].
3. Ayrı ses kanalları ortak zaman ekseninde hizalanmış, enerji tabanlı çok kanallı VAD ile tekil ve örtüşen konuşmalar yapısal segmentlere dönüştürülmüştür.
4. RTTM ve zaman çizelgesi çıktıları üzerinden toplantı davranışını nicel olarak incelemeyi mümkün kılan bir metrik katmanı kurulmuştur.
5. LangGraph ile tanımlanan ajan grafı sayesinde transkripsiyon, özetleme ve aksiyon çıkarımı görevleri paylaşımlı durum üzerinde modüler biçimde orkestre edilmiştir [13][14].
6. Üretilen çıktılar toplantı detay ekranına, konuşma zaman çizelgesine ve aksiyon maddesi görünümüne aktarılmıştır.

## 6. Bölüm 2: İlgili Çalışmalar

### 6.1 WebRTC, SFU ve Toplantı Medya Altyapıları

Modern toplantı sistemleri, medya akışlarının tek tek uç noktalar arasında dağınık biçimde taşındığı salt eşler arası yapılardan ziyade, seçici iletim birimi (Selective Forwarding Unit, SFU) kullanan merkezi yapılara yönelmiştir. Bu yaklaşım, katılımcı sayısı arttığında yayın ve abonelik düzlemlerini daha yönetilebilir hale getirir. LiveKit istemci protokolü, istemcilerin sunucuyla WebSocket üzerinden sinyalleştiğini ve yayın ile abonelik için WebRTC bağlantılarının kullanıldığını açıkça ortaya koymaktadır [1]. Bu özellik, konuşma odaklı toplantı uygulamalarında istemci tarafındaki karmaşıklığı azaltırken, sunucu tarafında olay takibi ve medya yönlendirmesini daha denetlenebilir hale getirir.

Bu çalışmada medya edinim katmanı LiveKit üzerinde kuruludur. LiveKit track egress yaklaşımı, tekil bir izi doğrudan dışa aktararak katılımcı ayrımını iz seviyesinde korur [3]. Bu tercih, özellikle konuşmacı bazlı ses çözümlemesi açısından belirleyicidir; çünkü ayrık ses kanalları doğrudan analize girer ve kayıt yaşam döngüsü oda, katılımcı, bağlantı ve iz olaylarıyla birlikte denetlenebilir hale gelir. Böylece medya katmanı ile analiz katmanı arasında açık ve izlenebilir bir veri hattı kurulmuş olur.

LiveKit ayrıca webhook mekanizmasıyla oda, katılımcı ve iz olaylarını arka uç servise imzalı biçimde iletebilmektedir [2]. Bu sayede oturumun başlama, katılımcıların bağlanma-ayrılma ve izlerin yayınlanma-yayından kalkma olayları arka uç tarafından doğrulanabilir ve zaman damgalı bir günlük yapısına dönüştürülebilir. Bu çalışma açısından bu özellik önemlidir; çünkü konuşma analizi yalnızca ses dosyalarına değil, bu ses dosyalarının hangi katılımcıya, hangi bağlantıya ve hangi zaman aralığına ait olduğuna da ihtiyaç duymaktadır.

### 6.2 ASR ve Toplantı Transkripsiyonu

Toplantı analizi boru hattının ikinci temel bileşeni otomatik konuşma tanımadır. Whisper, büyük ölçekli zayıf denetimli veri üzerinde eğitilmiş çok dilli bir ASR modeli olarak toplantı konuşması gibi gürültülü ve çok konuşmacılı bağlamlarda güçlü bir başlangıç noktası sunmaktadır [5]. Güncel implementasyonda model doğrudan orijinal `openai/whisper` paketiyle değil, CTranslate2 tabanlı `faster-whisper` üzerinden kullanılmaktadır. Bu tercih, benzer doğrulukta daha hızlı çıkarım ve daha düşük bellek tüketimi nedeniyle ürünleşme açısından anlamlıdır [6].

Bu tezde transkripsiyonun yalnızca "ses dosyasını yazıya çevirme" işlemi olarak anlatılması yeterli değildir. Güncel sistemde her katılımcı için seçilen en güncel ses dosyası ayrı ayrı çözümlenmekte, her segment için konuşmacı adı ve zaman ofseti korunmakta, ardından segmentler birleşik bir toplantı transkriptine dönüştürülmektedir. Bu tasarım, klasik tek dosya transkripsiyonundan farklı olarak konuşmacı kimliğini ASR aşamasına dışarıdan enjekte eder; yani ASR modeli konuşmacıyı tahmin etmez, sistem mimarisi konuşmacıyı zaten bilir. Bu ayrım tezde açık biçimde vurgulanmalıdır.

### 6.3 Çok Kanallı VAD, Konuşmacı Ayrımı ve Overlap Modelleme

Konuşmacı ayrımı literatürü büyük ölçüde tek kanallı ses, gömme çıkarımı ve kümeleme temelli diarization problemleri etrafında şekillenmiştir. pyannote.audio bu alanın temel araçlarından biri olarak VAD, speaker change detection, overlapped speech detection ve speaker embedding gibi yapı taşları sağlamaktadır [7]. Bununla birlikte toplantı verisinin bireysel mikrofonlardan toplanabildiği durumlarda problem yapısı değişmektedir. AMI Meeting Corpus, özellikle IHM kayıtları sayesinde bu bakış açısı için önemli bir referans oluşturmaktadır [8].

Bu tezde önerilen güncel yaklaşım, tek kanallı diarization yerine çok kanallı konuşma segmentasyonu olarak tanımlanmalıdır. Çünkü sistemin elinde katılımcı başına ayrılmış ses izleri bulunmaktadır. Buradaki asıl problem, "bu sesi kim konuştu?" sorusundan çok, "hangi kanallar hangi zaman aralığında gerçekten aktifti, hangi bölgeler mikrofon sızıntısıydı, hangi bölgeler gerçek overlap idi?" sorusuna dönüşmektedir. Bu nedenle tezde "speaker diarization" terimi tamamen terk edilmemeli, fakat çalışma zamanındaki çekirdek yöntemin aslında "çok kanallı kanal-etkinlik çözümlemesi" olduğu net biçimde yazılmalıdır.

### 6.4 Toplantı Özetleme ve Aksiyon Maddesi Çıkarımı

Toplantı özetleme alanında, çok konuşmacılı diyalogların uzun bağlam yapısı, konu kaymaları ve örtük karar ifadeleri önemli zorluklar doğurmaktadır. Rennard ve arkadaşlarının derlemesi, veri kümeleri, modeller ve değerlendirme ölçütleri açısından alanın kapsamlı bir görünümünü sunmaktadır [9]. Asthana ve arkadaşlarının çalışması ise toplantı sonrası çıktının yalnızca tek tip özetten ibaret olmaması gerektiğini; özet, vurgu ve aksiyon maddeleri gibi farklı özet biçimlerinin farklı kullanıcı ihtiyaçlarına hizmet ettiğini göstermektedir [10].

Aksiyon maddesi çıkarımı yerleşik bir araştırma çizgisine sahiptir. Bennett ve Carbonell, toplantı metinlerinden aksiyon maddesi tespiti için olasılık tabanlı sıralama yaklaşımlarını incelemiştir [11]. Daha güncel çalışmalarda ise bağlam modelleme ve önceden eğitilmiş dil modelleriyle bu görev daha yüksek doğrulukla ele alınmaktadır [12]. Güncel sistemde aksiyon maddeleri, serbest biçimli bir sohbet çıktısı olarak değil, yapılandırılmış JSON üretimiyle elde edilmektedir. Bu tasarım, tezde önemli bir mühendislik kararı olarak anlatılmalıdır; çünkü yapılandırılmış çıktı üretimi, ürün arayüzünde doğrudan kullanılabilir veri oluşturmak açısından kritik önemdedir.

### 6.5 LangGraph ve Ajan Orkestrasyonu

LangGraph, paylaşımlı durum üzerinde çalışan çok adımlı ajan iş akışlarını graf biçiminde tanımlamayı sağlayan düşük seviyeli bir orkestrasyon çerçevesidir [13][14]. Düğümler durumdan okur, kısmi durum güncellemeleri döndürür ve kenarlar yürütme sırasını belirler. Bu model, toplantı analizi gibi birden fazla uzmanlaşmış işlemin ortak bağlam üzerinde birlikte çalıştığı senaryolar için doğrudan uygundur.

Bu proje bağlamında LangGraph, analiz akışının yürütülebilir çekirdeğidir. `transcription_agent`, `summary_agent` ve `action_item_agent` düğümlerinden oluşan grafik, toplantı analizini açık bir durum makinesi halinde temsil etmektedir. Dolayısıyla tezde LangGraph'ın rolü iki düzeyde anlatılmalıdır:

1. Kavramsal düzeyde, toplantı analizi problemini uzman görevlerin paylaşımlı durum üzerinden koordine edildiği bir ajan sistemi olarak modellemektedir.
2. Uygulama düzeyinde, analiz iş akışının modülerliğini, genişletilebilirliğini ve hata ayrıştırmasını güçlendirmektedir.

Bu nokta özellikle önemlidir; çünkü güncel ürün mimarisinde LiveKit ve FastAPI operasyonel medya katmanını taşırken, LangGraph semantik analiz katmanının yürütme mantığını temsil etmektedir. Tezde bu iki katman ayrı ama bütünleşik biçimde anlatılmalıdır. Böylece sistem, medya edinimini, konuşma çözümlemesini ve ajan orkestrasyonunu aynı mimari çatı altında bir araya getiren çok katmanlı bir platform olarak sunulabilir.

### 6.6 Literatürdeki Boşluk ve Çalışmanın Konumu

Literatürdeki birçok sistem ya medya altyapısına, ya ASR kalitesine, ya da salt özetleme başarımına odaklanmaktadır. Buna karşılık bu çalışma, bireysel ses izlerini koruyan gerçek zamanlı medya toplama, çok kanallı etkinlik çözümlemesi ve ajan orkestrasyonunu aynı ürün mimarisi içinde birleştirmektedir. Bu nedenle çalışma, tek bir model önerisinden çok, birbirine bağlı kararların oluşturduğu sistem düzeyi bir katkı olarak çerçevelenmelidir.

## 7. Bölüm 3: Yöntem ve Sistem Tasarımı

\chapter{\TRorEN{YÖNTEM}{METHODOLOGY}}
\label{ch:method}

Bu bölümde geliştirilen Akıllı Toplantı Analiz Sisteminin tasarım ilkeleri, yöntemsel yaklaşımı, sistem mimarisi ve yazılım bileşenleri bütüncül bir çerçevede sunulmaktadır. Çalışma, sistem tasarımı yaklaşımı kapsamında ele alınmış; toplantı planlama, gerçek zamanlı medya edinimi, konuşma çözümleme, otomatik transkripsiyon, büyük dil modeli tabanlı toplantı analizi ve kullanıcı arayüzü katmanları birbirine bağlı alt sistemler olarak modellenmiştir. Bu doğrultuda sistem, yalnızca çevrim içi toplantıyı yürütmeyi değil, toplantı sırasında oluşan medya verisini sonradan analiz edilebilir, yapılandırılabilir ve eyleme dönüştürülebilir bir kurumsal hafıza nesnesine dönüştürmeyi hedeflemektedir.

Bu bölüm dört ana başlık altında yapılandırılmıştır. İlk olarak metodolojik yaklaşım ve tasarım mantığı açıklanmakta, ardından sistemin genel tasarım çerçevesi verilmektedir. Sonraki aşamada sistem mimarisi, birbirine entegre işlevsel katmanlar üzerinden ayrıntılı biçimde incelenmektedir. Son olarak sistem yazılımı; arka uç servisleri, veri saklama yapıları, analiz çıktıları, ön yüz entegrasyonu ve dağıtım bileşenleri bakımından ele alınmaktadır.

\section{Metodoloji}
\label{sec:metodoloji}

Bu çalışmanın metodolojik çıkış noktası, toplantı analizini yalnızca metin işleme problemi olarak değil, veri ediniminden başlayan uçtan uca bir sistem problemi olarak tanımlamaktır. Literatürde çok konuşmacılı toplantı çözümlemesi çoğunlukla konuşma ayırma, diarization ve otomatik konuşma tanıma bileşenlerinin ardışık biçimde çalıştırıldığı modüler boru hatları ile ele alınmaktadır. Raj ve diğ.\ tarafından önerilen \textit{Integration of Speech Separation, Diarization, and Recognition} çalışması bu yaklaşımın temsil edici örneklerinden biridir \cite{raj2021}. Bu tip sistemlerde karışık ses kaydı üzerinde önce hangi sesin hangi konuşmacıya ait olduğu tahmin edilmekte, daha sonra transkripsiyon ve üst düzey toplantı analizi gerçekleştirilmektedir.

Ancak bu yaklaşım özellikle örtüşen konuşmanın yoğun olduğu toplantılarda hata zinciri üretmeye eğilimlidir. Tek kanallı veya karışık çok kanallı ses verisi üzerinde çalışan diarization yöntemleri genellikle VAD, speaker embedding çıkarımı, benzerlik ölçümü, kümeleme ve segment düzeltme gibi çok aşamalı süreçlere ihtiyaç duyar. \textit{pyannote.audio: Neural Building Blocks for Speaker Diarization}, \textit{Powerset Multi-Class Cross Entropy Loss for Neural Speaker Diarization}, \textit{Speaker Diarization: A Review} ve \textit{SDBench: A Comprehensive Benchmark Suite for Speaker Diarization} gibi çalışmalar bu problem alanının hem önemini hem de zorluğunu göstermektedir \cite{bredin2020,plaquet2023,oshaughnessy2025,pacheco2025}.

Bu tezde ise farklı bir yöntemsel tercih benimsenmiştir. Konuşmacı kimliği sonradan tahmin edilmek yerine veri edinim katmanında korunmaktadır. Sistem, LiveKit tabanlı WebRTC mimarisi üzerinden her katılımcının mikrofon izini ayrı bir ses izi olarak üretmekte ve bu izleri bağımsız ses dosyaları halinde kaydetmektedir. Böylece klasik diarization probleminin en zor bileşeni olan ``kim konuştu'' sorusu, öğrenmeye dayalı bir tahmin problemi olmaktan çıkarılıp sistem düzeyinde çözülmektedir. Problem, bu noktadan sonra ``hangi katılımcı kanalı hangi zaman aralığında gerçekten aktifti'' ve ``gerçek overlap bölgeleri hangileridir'' biçiminde yeniden tanımlanmaktadır.

Bu yaklaşım, çok kanallı toplantı verisinin önemini vurgulayan \textit{The AMI Meeting Corpus} ve uzamsal-spektal bileşenlerin çok kanallı diarization üzerindeki etkisini tartışan \textit{Loose Coupling of Spectral and Spatial Models for Multi-Channel Diarization and Enhancement of Meetings in Dynamic Environments} gibi çalışmalarla kavramsal olarak uyumludur \cite{mccowan2005,meise2026}. Bununla birlikte önerilen sistem, bu çalışmalardan farklı olarak konuşmacı ayrımını doğrudan mimari tasarımın içine gömerek daha deterministik bir çözüm sunmaktadır.

Metodolojik yaklaşımın ikinci boyutu, üst düzey toplantı yorumlama katmanında görev ayrımı yapılmasıdır. Literatürde birçok toplantı özetleme sisteminde tek bir büyük dil modeline tüm görevlerin bir arada yüklendiği monolitik tasarımlar görülmektedir. Ancak özetleme, karar çıkarımı ve aksiyon maddesi tespiti gibi görevlerin aynı istem bağlamı içinde çözülmesi; bağlam karmaşası, hata yayılımı ve denetlenebilirlik kaybı yaratabilmektedir. Bu nedenle bu çalışmada, çok-etmenli sistemlerin görev paylaşımı ve yanıt tutarlılığına ilişkin bulgularından yararlanılmıştır. \textit{Scalable Multi-Robot Collaboration with LLMs: CMAS vs DMAS}, \textit{Modeling Response Consistency in Multi-Agent LLM Systems}, \textit{ScheduleMe: Multi-Agent Calendar Assistant} ve \textit{Multi-Agent LLM System for Meeting Info Processing} gibi çalışmalar, uzmanlaşmış görev ayrımının karmaşık iş akışlarında ölçeklenebilirlik ve tutarlılık bakımından avantaj sağladığını göstermektedir \cite{chen2024,helmi2025,wijerathne2025,varju2025}.

Bu nedenle önerilen sistemde toplantı çözümleme katmanı tek bir serbest LLM çağrısı olarak değil, paylaşılan durum üzerinden çalışan uzman görevler bütünü olarak modellenmiştir. Transkripsiyon, özetleme ve aksiyon maddesi çıkarımı birbirinden ayrılmış; bu görevler hem ürünleşmiş servis katmanında hem de deneysel LangGraph grafında modüler bileşenler halinde tasarlanmıştır.

\section{Tasarım Genel Bakışı}
\label{sec:tasarim_genel_bakis}

Bu çalışmada geliştirilen sistem, çevrim içi toplantı ortamlarında katılımcı yönetimi, medya akışlarının toplanması, konuşma etkinliğinin çıkarılması, otomatik transkripsiyon, toplantı özeti üretimi, aksiyon maddesi belirleme ve raporlama işlevlerini entegre biçimde gerçekleştiren çok katmanlı bir Akıllı Toplantı Analiz Sistemi olarak tasarlanmıştır. Sistem, toplantının planlanmasından başlayarak oturum oluşturma, gerçek zamanlı bağlanma, ses izi kaydı, konuşma çözümleme, yapay zekâ destekli içerik analizi ve ön yüzde sunum aşamalarına kadar uzanan uçtan uca bir iş akışı sunmaktadır.

Tasarımın temel yeniliği, konuşmacı ayrımını sonradan çözülecek bir tahmin problemi olarak ele almamasıdır. Geleneksel speaker diarization yaklaşımlarında VAD, embedding extraction ve clustering zinciri üzerinden çalışan çok aşamalı yapılar kullanılmaktadır. Bu yapıların özellikle overlapped speech içeren toplantılarda performans kaybına uğradığı; \textit{Benchmarking Diarization Models}, \textit{Speaker Diarization: A Review} ve \textit{An Experimental Review of Speaker Diarization Methods} gibi çalışmalarda ayrıntılı biçimde tartışılmaktadır \cite{lanzendorfer2025,oshaughnessy2025,serafini2023}. Önerilen sistemde ise her katılımcının sesi zaten ayrı track olarak üretildiğinden konuşmacı kimliği medya katmanında korunmakta ve sonraki analiz katmanı daha sade bir problem uzayı üzerinde çalışmaktadır.

Sistemin ikinci temel özelliği, konuşma analizi ile semantik toplantı analizinin birbirinden ayrılmış ancak bütünleşik iki düzlemde ele alınmasıdır. İlk düzlemde ses standardizasyonu, zaman hizalama, enerji tabanlı çok kanallı VAD, overlap tespiti ve RTTM üretimi gerçekleştirilmektedir. İkinci düzlemde ise \textit{Robust Speech Recognition via Large-Scale Weak Supervision} çalışmasında temellenen Whisper ailesi ve onun verimli uygulamalarından biri olan \texttt{faster-whisper} kullanılarak transkripsiyon üretilmekte; ardından toplantı özetleme literatürüyle uyumlu şekilde özet, karar ve aksiyon maddeleri çıkarılmaktadır \cite{radford2022robust,fasterWhisper,rennard2023,asthana2025,asha2025}.

Sistemin genel mantığı aşağıdaki veri akışıyla özetlenebilir:
\[
\text{Toplantı Planlama}
\rightarrow
\text{Oturum ve Token Üretimi}
\rightarrow
\text{LiveKit Oda Bağlantısı}
\rightarrow
\text{Track-Level Ses Kaydı}
\rightarrow
\text{Çok Kanallı Konuşma Analizi}
\rightarrow
\text{ASR}
\rightarrow
\text{LLM Tabanlı Özet ve Aksiyon Çıkarımı}
\rightarrow
\text{React Tabanlı Raporlama}
\]

Bu yapı, toplantı destek sistemlerinin tarihsel örneklerinden biri olan \textit{The CALO Meeting Assistant System} ile benzer biçimde toplantıyı anlamlandırılabilir bir çalışma nesnesi haline getirmeyi amaçlamakta; ancak güncel gerçek zamanlı medya altyapısı ve büyük dil modeli tabanlı analiz yetenekleri ile bunu daha modüler ve üretim odaklı bir forma taşımaktadır \cite{tur2010}.

\section{Sistem Mimarisi}
\label{sec:sistem_mimarisi}

Önerilen sistem mimarisi, birbirine entegre yedi işlevsel katmandan oluşmaktadır. Her katman bağımsız olarak geliştirilebilir ve test edilebilir olmakla birlikte, katmanlar arası veri akışı JSON uyumlu veri yapıları ve dosya çıktıları üzerinden sağlanmaktadır. Genel mimari Şekil~\ref{fig:system_architecture} üzerinde özetlenmiştir.

\begin{figure}[htbp]
\centering
\fbox{
\begin{minipage}{0.94\linewidth}
\centering
Toplantı Planlama ve React Arayüzü
$\rightarrow$
FastAPI Oturum ve Token Servisleri
$\rightarrow$
LiveKit Oda / Webhook / Track Egress
$\rightarrow$
SessionStore + Kayıt Dosyaları
$\rightarrow$
SpeechAnalysisService
$\rightarrow$
ASR Katmanı
$\rightarrow$
AIAnalysisService / LangGraph Etmenleri
$\rightarrow$
Özet, Kararlar, Aksiyon Maddeleri, Zaman Çizelgesi ve Dashboard
\end{minipage}
}
\caption{Akıllı Toplantı Analiz Sistemi genel mimarisi}
\label{fig:system_architecture}
\end{figure}

\subsection{Katman 1 --- Toplantı Planlama ve Kullanıcı Etkileşimi}

Sistemin giriş katmanı toplantı planlama ve kullanıcı etkileşimini kapsamaktadır. Bu katmanda kullanıcılar toplantı başlığı, açıklama, planlanan başlangıç ve bitiş zamanı, gündem maddeleri ve katılımcı bilgilerini tanımlamaktadır. Bu veriler uygulama düzeyinde \texttt{MeetingStore} üzerinde saklanmakta ve toplantı başlamadan önce toplantının yapısal bağlamını oluşturmaktadır. Böylece sistem, yalnızca canlı medya akışını işleyen bir araç olmaktan çıkarak planlı toplantılar üzerinde çalışan kurumsal bir uygulama yapısına kavuşmaktadır.

Ön yüz tarafında kullanıcı, toplantı listesi, toplantı oluşturma ekranı, canlı toplantı odası ve toplantı detay/analiz ekranı arasında gezinebilmektedir. Toplantı detay ekranı daha sonra üretilecek konuşma analizi ve AI özet çıktılarının sunulduğu ana raporlama alanı olarak görev yapmaktadır.

\subsection{Katman 2 --- Oturum Yönetimi, Token Üretimi ve LiveKit Entegrasyonu}

Toplantının gerçek zamanlı yürütülmesi için sistem, LiveKit tabanlı WebRTC altyapısı kullanmaktadır. LiveKit istemci-sunucu protokolünün çalışma biçimi, \textit{Client Protocol} dokümantasyonunda ayrıntılı biçimde tanımlanmaktadır \cite{LiveKitClientProtocol}. Bu mimaride arka uç, toplantı başladığında önce LiveKit üzerinde ilgili oturum için bir oda hazırlamakta; daha sonra her katılımcı için benzersiz bir katılımcı kimliği ve erişim belirteci üretmektedir. Bu belirteç içinde katılımcı kimliği, görünür ad ve cihaz bilgisi gibi meta veriler taşınmaktadır.

İstemci, oluşturulan bu belirteç ile LiveKit odasına bağlanmakta ve mikrofon ile kamera yayınlarını başlatmaktadır. Ön yüzde bağlantı durumu, yeniden bağlanma senaryoları, aktif konuşmacı olayları, katılımcı listesi ve medya kontrolleri canlı olarak yönetilmektedir. Bağlantı kurulduğunda arka uç ayrıca katılımcı bağlantı bilgisini ve stream eşlemesini kayıt altına almaktadır. Böylece uygulama düzeyindeki katılımcı kimliği ile gerçek zamanlı medya düzeyindeki bağlantı ve track kimlikleri eşleştirilmektedir.

\subsection{Katman 3 --- Webhook Tabanlı Olay İşleme ve Track-Level Kayıt}

Canlı toplantı sırasında oluşan tüm önemli medya olayları, LiveKit'in webhook mekanizması üzerinden arka uca iletilmektedir. \textit{Webhooks \& Events} dokümantasyonunda açıklandığı üzere oda başlama, katılımcı katılma-ayrılma, track yayınlama ve yayın kaldırma olayları bu kanal üzerinden izlenebilir durumdadır \cite{LiveKitWebhooksAndEvents}. Sistem, her webhook olayını önce doğrulamakta, sonra oturum günlüğüne yazmakta ve ilgili oturum meta verisini güncellemektedir.

Bu katmanın en kritik görevi, mikrofon izleri yayınlandığında her katılımcı için ayrı track egress süreci başlatmaktır. LiveKit'in \textit{Track Egress} özelliği, tek bir medya izinin bağımsız dosya olarak dışa aktarılmasına olanak vermektedir \cite{LiveKitTrackEgress}. Bu sayede sistem, toplantı tamamlandığında karışık tek bir ses kaydı yerine katılımcı başına ayrı ses dosyalarına sahip olmaktadır. Her kayıt için track kimliği, bağlantı kimliği, dosya yolu, başlangıç zamanı ve bitiş zamanı oturum durumuna kaydedilmektedir.

Bu yaklaşım mimari açıdan son derece önemlidir. Çünkü konuşmacı ayrımı ses sinyalinden sonradan çıkarılmak yerine, veri edinim tasarımı sayesinde baştan korunmuş olur. Böylece sonraki analiz aşamalarında konuşmacı kimliğini tahmin etmeye yönelik karmaşık embedding ve clustering katmanlarına ihtiyaç önemli ölçüde azalır.

\subsection{Katman 4 --- Oturum Durumu ve Veri Saklama Altyapısı}

Sistem iki farklı veri saklama yaklaşımını birlikte kullanmaktadır. Birinci yapı olan \texttt{MeetingStore}, ilişkisel toplantı verilerini SQLite üzerinde tutmaktadır. Bu yapı; toplantı başlığı, organizatör bilgileri, planlanan zaman, katılımcılar ve gündem maddeleri gibi nispeten durağan ve ilişkisel nitelikteki veriler için uygundur. İkinci yapı olan \texttt{SessionStore} ise JSON tabanlı oturum saklama katmanıdır ve oturum süresince değişen dinamik alanları taşımaktadır.

\texttt{SessionStore} içinde aşağıdaki ana alanlar tutulmaktadır:
\begin{itemize}
\item oturum kimliği ve genel oturum durumu,
\item katılımcı listesi ve bağlantı eşlemeleri,
\item yayınlanan stream bilgileri,
\item kayıt yaşam döngüsü ve üretilen medya dosyaları,
\item konuşma analizi durumu ve çıktıları,
\item AI analizi durumu ve çıktıları,
\item webhook olay günlüğü ve meta veriler.
\end{itemize}

Bu hibrit saklama tasarımı, toplantı planlama verilerinin ilişkisel bütünlüğünü korurken, canlı oturum sırasında değişen yarı-yapısal verilerin esnek biçimde saklanmasına imkân tanımaktadır. Ayrıca her oturum için ayrı klasör ve JSON dosyası tutulması, sistemin denetlenebilirliğini ve hata ayıklanabilirliğini artırmaktadır.

\subsection{Katman 5 --- Çok Kanallı Konuşma Analizi}

Konuşma analizi katmanı, toplantı sona erdiğinde veya tüm aktif egress süreçleri tamamlandığında çalışmaktadır. Bu katman, katılımcı başına kaydedilmiş ses dosyalarını standartlaştırmakta, ortak zaman eksenine hizalamakta, kanal bazlı ses etkinliklerini çıkarmakta, overlap bölgelerini belirlemekte ve sonuçları hem zaman çizelgesi hem de RTTM biçiminde üretmektedir.

\paragraph{Ses kaynaklarının toplanması ve ön temizleme.}
Sistem, oturum içinde kaydı bulunan gerçek katılımcıları toplamakta ve sistem-içi yardımcı katılımcıları analiz dışında bırakmaktadır. Her katılımcı için \texttt{recording\_files} alanında tutulan dosyalar üzerinden ses kaynakları seçilir. Bu yapı, aynı katılımcının birden fazla track yeniden yayını veya yeniden bağlanma senaryosu yaşadığı durumlarda birden fazla kayıt oluşmasına da izin verir.

\paragraph{Ses standardizasyonu.}
Ham ses kayıtları farklı tarayıcı, codec ve kapsayıcı biçimlerinde üretilebildiği için tüm dosyalar ortak bir temsil biçimine dönüştürülmektedir. \texttt{AudioStandardizer} bileşeni, mümkünse FFmpeg, gerekirse PyDub kullanarak sesi 16~kHz örnekleme hızına, tek kanala ve 16-bit PCM biçimine dönüştürmektedir. Ardından tepe değer normalizasyonu uygulanarak örnekler $[-1,1]$ aralığında ölçeklenmektedir. Bu adım, sonraki VAD ve ASR modüllerinin tutarlı giriş dağılımı görmesini sağlamaktadır. Bu bakımdan sistemin yaklaşımı, konuşma ön işlemenin ASR doğruluğu üzerindeki önemini vurgulayan \textit{Real-Time Smart Meeting Assistant using Edge AI for Audio Capture, Speech-to-Text Conversion, and Meeting Scheduling} çalışmasıyla da uyumludur \cite{senthilselvi2025}.

\paragraph{Zaman hizalama.}
Her katılımcı kaydı aynı anda başlamayabileceğinden sistem, tüm ses izlerini ortak zaman eksenine yerleştirmektedir. Bunun için her dosyanın başlangıç ofseti örnek sayısına dönüştürülmekte ve ilgili ses sinyali bu ofsete göre hedef dizi içine yerleştirilmektedir. Kayıt meta verisinde belirtilen beklenen süre ile gerçek dalga formu uzunluğu karşılaştırılmakta; gerekirse sıfır dolgusu eklenmekte veya fazla örnekler kırpılmaktadır. Aynı katılımcıya ait parçalı kayıtlar çakışıyorsa mutlak genliği daha yüksek örnekler korunmaktadır. Sonuçta her katılımcı için toplantının tamamına yayılmış hizalanmış bir kanal elde edilir.

\paragraph{Kanal bazlı VAD.}
Her kanal üzerinde enerji tabanlı adaptif VAD çalıştırılmaktadır. \texttt{EnergyVAD} bileşeni, sesi 25~ms çerçevelere bölmekte ve 10~ms adım ile kayan pencere analizi yapmaktadır. Her çerçeve için RMS enerji hesaplanmakta; ardından 30 saniyelik adaptif pencere üzerinden yerel minimum enerji ve küresel yüzde~10'luk enerji değeri birlikte kullanılarak gürültü tahmini çıkarılmaktadır. Eşik değeri aşağıdaki gibi hesaplanmaktadır:
\[
\hat{n}_k(t)=0.7 \cdot \min(E_k[t-W,t]) + 0.3 \cdot P_{10}(E_k)
\]
\[
\theta_k(t)=\max\left(2.5 \cdot \hat{n}_k(t),\,0.02\right)
\]
Burada $\hat{n}_k(t)$, $k$ kanalına ait anlık gürültü kestirimi; $E_k$ RMS enerji dizisi; $P_{10}(E_k)$ ise kanalın tüm enerji dağılımı içindeki yüzde~10'luk sessiz bölge istatistiğidir. Sabit eşik yerine minimum istatistik tabanlı bu yaklaşım, sürekli konuşmanın görüldüğü kanallarda eşik değerinin aşırı yükselmesini engellemektedir.

\paragraph{Spektral düzey filtresi.}
Enerji eşiğine ek olarak her çerçeve için Spectral Flatness Measure (SFM) hesaplanmaktadır. Konuşma sinyalleri daha harmonik yapıda olduğu için SFM değeri düşük; düz spektrumlu gürültüde ise daha yüksektir. Sistem, bir çerçeveyi yalnızca şu koşul sağlandığında aktif kabul etmektedir:
\[
a_k(t)=1 \iff E_k(t)>\theta_k(t)\ \land\ \mathrm{SFM}_k(t)<0.6
\]
Bu ek kontrol, yalnızca enerjiye bakıldığında konuşma olarak işaretlenebilecek bazı gürültü örneklerini baskılamaktadır.

\paragraph{Global sessizlik kapısı.}
Bir zaman çerçevesinde tüm kanalların maksimum enerjisi $0.03$ değerinin altındaysa, sistem bunu gerçek sessizlik olarak değerlendirmekte ve hiçbir kanalı aktif kabul etmemektedir:
\[
\max_j E_j(t)<0.03 \Rightarrow a_k(t)=0,\ \forall k
\]
Bu kural, sessiz bölümlerde yanlış konuşmacı etkinliği üretimini azaltmaktadır.

\paragraph{Cross-channel bleed bastırma.}
Çok katılımcılı toplantılarda mikrofon sızıntısı nedeniyle zayıf bir kanal, başka bir konuşmacının sesiyle yanlış biçimde aktif görünebilir. Bu problemi azaltmak için sistem aşağıdaki bastırma kuralını uygulamaktadır:
\[
E_k(t) < 0.15 \cdot \max_j E_j(t) \Rightarrow a_k(t)=0
\]
Bu mekanizma, özellikle aynı fiziksel ortamda bulunan mikrofonlarda sahte overlap tespitlerini azaltmaktadır.

\paragraph{Dominant-only baskılama.}
Bleed baskılamasından sonra hâlâ birden fazla kanal aktif görünüyorsa, sistem baskın enerji oranını inceler. En güçlü kanal enerjisinin ikinci en güçlü aktif kanal enerjisine oranı $5.0$ değerinden büyükse yalnızca baskın kanal korunur:
\[
\frac{E_{\max}(t)}{E_{\text{second}}(t)} > 5.0 \Rightarrow
\text{yalnızca baskın kanal aktif}
\]
Bu kural, gerçek overlap ile baskın konuşma etrafındaki zayıf sızıntıyı birbirinden ayırmak için kullanılmaktadır.

\paragraph{Aktivite matrisinden segment üretimi.}
Tüm kanallar için elde edilen etkinlik kararları bir aktivite matrisinde birleştirilir. Her zaman adımında aktif kanal sayısına göre üç durum tanımlanır:
\begin{itemize}
\item aktif kanal yoksa sessizlik,
\item tek aktif kanal varsa \texttt{single} segment,
\item birden fazla aktif kanal varsa \texttt{overlap} segment.
\end{itemize}
Durum değiştiğinde yeni bir segment başlatılmakta, segment başlangıç ve bitiş zamanları çerçeve zamanlarından hesaplanmaktadır. Daha sonra süresi 200~ms'den kısa segmentler bağımsız segment olarak korunmamakta, bir önceki segmentle birleştirilmektedir. Bu filtreleme adımı, ani gürültü kaynaklı mikroseviye aktivasyonları bastırmakta ve etiketlerin kararlılığını artırmaktadır.

\paragraph{RTTM üretimi ve metrikler.}
Konuşma analizi sonunda elde edilen segmentler iki ana çıktı biçimine dönüştürülmektedir. Birincisi, kullanıcı arayüzünde kullanılacak yapılandırılmış zaman çizelgesi verisidir. İkincisi ise \texttt{RTTMWriter} ile oluşturulan RTTM dosyasıdır. Burada overlap bölgeleri sahte bir ``overlap'' konuşmacısı olarak değil, ilgili her konuşmacı için ayrı RTTM satırı olarak yazılmaktadır. Bu karar, \textit{pyannote.audio: Neural Building Blocks for Speaker Diarization} ekosistemiyle uyumluluğu korumaktadır \cite{bredin2020}.

Ayrıca sistem, toplam kayıt süresi, işleme süresi, aktif konuşma süresi, overlap süresi, sessizlik süresi, segment sayısı, ortalama segment uzunluğu, medyan segment uzunluğu ve dakika başına segment yoğunluğu gibi genel metrikler hesaplamaktadır. Katılımcı bazında ise toplam konuşma süresi, overlap içinde yer alma süresi, ilk ve son konuşma zamanı ile toplam kayda göre konuşma yüzdesi ve aktif konuşmaya göre konuşma yüzdesi üretilmektedir. Bu nicel özetler toplantı sonrası analitik ekranın temelini oluşturmaktadır.

\subsection{Katman 6 --- Otomatik Transkripsiyon}

Konuşma analizi sonrasında ya da doğrudan katılımcı ses kaynakları üzerinden yürütülen ikinci temel işlem, ses segmentlerinin metne dönüştürülmesidir. Bu katmanda OpenAI Whisper ailesinin verimli uygulaması olan \texttt{faster-whisper} kullanılmaktadır. Whisper modelinin gerçek dünya konuşma koşullarındaki dayanıklılığı \textit{Robust Speech Recognition via Large-Scale Weak Supervision} çalışmasıyla ortaya konmuştur \cite{radford2022robust}. Uzun toplantı transkriptleri ve toplantı yardımcısı bağlamında ASR performansının önemi ise \textit{ELITR-Bench: A Meeting Assistant Benchmark for Long-Context Language Models} gibi çalışmalarda vurgulanmaktadır \cite{thonet2025}.

Sistemde transkripsiyon katmanı şu adımlarla çalışmaktadır:
\begin{enumerate}
\item seçilen ses dosyası FFmpeg ile 16~kHz mono dalga biçimine dönüştürülür,
\item model Türkçe dil ayarı ile çağrılır,
\item beam size değeri $5$ olarak kullanılır,
\item sıcaklık değeri $0.0$ tutulur,
\item \texttt{condition\_on\_previous\_text=False} seçilerek segmentler arası istem aktarımı kapatılır,
\item VAD filtreli çalıştırma varsayılan olarak açıktır,
\item anlamlı segment gelmezse gevşek filtre eşikleri ve gerekirse VAD kapalı yedek yol devreye alınır.
\end{enumerate}

İlk geçişte segmentlerin kabulü için şu kalite ölçütleri uygulanmaktadır:
\begin{itemize}
\item en az 3 karakter,
\item en az 2 kelime,
\item \texttt{no\_speech\_prob} değeri en çok $0.50$,
\item \texttt{avg\_logprob} değeri en az $-1.0$.
\end{itemize}

Eğer yeterli çıktı üretilemezse sistem daha gevşek bir modda tekrar dener; bu durumda tek kelimelik segmentler kabul edilebilir, \texttt{no\_speech\_prob} eşiği $0.75$'e çıkarılır ve \texttt{avg\_logprob} alt sınırı $-1.6$'ya düşürülür. Son aşamada gerekirse VAD kapalı transkripsiyon uygulanır. Bu çok kademeli fallback mekanizması, hem sessiz/gürültülü kayıtların boşa düşmesini önlemekte hem de anlamsız hallüsinasyon üretimini sınırlamaktadır.

Her transkripsiyon segmenti konuşmacı adı, katılımcı kimliği, başlangıç zamanı, bitiş zamanı ve metin ile birlikte saklanmaktadır. Birden fazla katılımcıdan gelen segmentler daha sonra başlangıç zamanına göre sıralanarak birleşik toplantı transkripti oluşturulmaktadır. Böylece sistem, konuşmacı etiketli tam metin döküm üretmektedir. Bu tasarım, klasik tek dosya ASR yaklaşımından farklı olarak konuşmacı bilgisini modelin kendisinden beklememekte; bu bilgiyi mimarinin önceki katmanlarından devralmaktadır.

\subsection{Katman 7 --- Çok-Etmenli Toplantı Analizi Katmanı}

Toplantıdan elde edilen yapılandırılmış transkript, sistemin en üst düzey semantik analiz katmanına aktarılmaktadır. Bu katmanın amacı, ham transkript verisini insan tarafından doğrudan kullanılabilir toplantı çıktısına dönüştürmektir. Bu bağlamda sistem; yönetici özeti, karar maddeleri, konu başlıkları ve aksiyon maddeleri üretmektedir. Toplantı özetleme alanında \textit{Abstractive Meeting Summarization: A Survey}, \textit{Automatic Meeting Summarization and Topic Detection} ve \textit{AutoMeet: Automated Meeting Summarization} gibi çalışmalar, toplantı içeriğinin üst düzey soyutlamalarına duyulan ihtiyacı göstermektedir \cite{rennard2023,huang2018,baeuerle2025}. Bu çalışmada önerilen analiz katmanı, bu ihtiyacı yapılandırılmış ve görev ayrımlı bir biçimde karşılamaktadır.

\paragraph{Paylaşılan durum modeli.}
Sistemin deneysel ajan orkestrasyon katmanında tüm etmenler \texttt{MeetingState} adlı merkezi durum nesnesi üzerinden iletişim kurmaktadır. Bu yapı aşağıdaki alanları içermektedir:
\begin{itemize}
\item katılımcı listesi,
\item toplantı tarihi,
\item dil bilgisi,
\item konuşma segmentleri,
\item birleşik transkript,
\item yönetici özeti ve hiyerarşik dakikalar,
\item kararlar,
\item konu başlıkları,
\item aksiyon maddeleri,
\item hata listesi,
\item tamamlanan etmenler listesi,
\item ön yüze uygun özet nesnesi.
\end{itemize}
Merkezi durum yaklaşımı, \textit{Modeling Response Consistency in Multi-Agent LLM Systems} çalışmasında vurgulanan bağlam tutarlılığı gereksinimiyle uyumludur \cite{helmi2025}.

\paragraph{LangGraph tabanlı görev ayrımı.}
Sistemin \texttt{agents} modülünde bu iş akışı, LangGraph üzerinde kurulan bir \texttt{StateGraph} ile modellenmiştir. \textit{LangGraph Overview} ve \textit{StateGraph API Reference} belgelerinde tarif edilen bu yaklaşımda her düğüm merkezi durumdan okur ve kısmi durum güncellemesi döndürür \cite{LangGraphOverview,StateGraph}. Bu projede tanımlanan üç temel düğüm şunlardır:
\begin{itemize}
\item \texttt{transcription\_agent},
\item \texttt{summary\_agent},
\item \texttt{action\_item\_agent}.
\end{itemize}
Akış, önce transkripsiyon ajanının çalışması ve ardından özet ile aksiyon ajanlarının paralel yürütülmesi biçimindedir. Bu ayrım, görevlerin birbirinden bağımsız test edilmesine ve hataların daha iyi izole edilmesine olanak tanımaktadır.

\paragraph{Ürünleşmiş AI analiz servisi.}
Üretim akışında \texttt{AIAnalysisService}, aynı görev ayrımını operasyonel düzeye taşımaktadır. Servis önce ses kaynaklarını toplamakta, her katılımcı için en güncel kayıt dosyasını seçmekte, transkript segmentlerini üretmekte ve birleşik tam metni oluşturmaktadır. Daha sonra aynı transkript üzerinde iki ayrı LLM çağrısı yapmaktadır:
\begin{itemize}
\item toplantı özeti ve karar/konu çıkarımı,
\item aksiyon maddesi çıkarımı.
\end{itemize}

LLM istemcisi Groq uyumlu bir sohbet tamamlama API'si kullanmaktadır ve varsayılan model \texttt{llama-3.3-70b-versatile} olarak tanımlanmıştır. Ancak burada asıl önemli nokta model adından çok çıktı biçimidir. Sistem, her iki görev için de modelden JSON nesnesi dönmesini zorunlu kılmaktadır. Böylece üretilen içerik, arayüzde doğrudan tüketilebilir yapılandırılmış veri haline gelmektedir.

\paragraph{Özetleme etmeni.}
Özetleme görevi, modelden aşağıdaki alanları üretmesini istemektedir:
\begin{itemize}
\item 2--4 cümlelik yönetici özeti,
\item en fazla 5 karar maddesi,
\item en fazla 5 konu başlığı.
\end{itemize}
İstem tasarımında modelin yalnızca transkriptte açıkça geçen bilgiye dayanması, yeni karar uydurmaması, tekrarlı maddeleri birleştirmesi ve JSON dışında metin üretmemesi zorunlu kılınmıştır. Bu yaklaşım, \textit{Summaries, Highlights, and Action Items} çalışmasında vurgulanan çok-biçimli toplantı özeti ihtiyacı ile örtüşmektedir \cite{asthana2025}.

\paragraph{Aksiyon maddesi etmeni.}
Aksiyon maddesi çıkarımı görevi, toplantıdan eyleme dönüştürülebilir öğeleri belirlemeyi amaçlamaktadır. Bu bağlamda \textit{MEETING DELEGATE: Intelligent Task Assignment and Notification} gibi çalışmalar, toplantı sonrası görev yönetiminin pratik önemini göstermektedir \cite{hu2025}. Sistemde aksiyon maddeleri için aşağıdaki alanlar üretilmektedir:
\begin{itemize}
\item görev açıklaması,
\item atanan kişi,
\item son tarih,
\item öncelik,
\item güven skoru,
\item görev tipi,
\item gözden geçirme gereksinimi.
\end{itemize}

Bu katmanda güvenilirliği artırmak için çeşitli koruyucu kurallar uygulanmaktadır. Modelin transkriptte açıkça geçmeyen görevler üretmesine izin verilmez. Atanan kişi yalnızca açıkça belliyse doldurulur. Göreli tarih ifadeleri mutlak takvim tarihine çevrilmez. Güven skoru $0.65$'in altındaki maddeler \texttt{needs\_review=True} olarak işaretlenir. Görev tipi alanı ise \texttt{direct}, \texttt{volunteer}, \texttt{implicit}, \texttt{conditional} veya \texttt{group} değerlerinden biriyle sınırlandırılmıştır. Böylece serbest üretim yerine yarı-denetlenebilir bir karar destek mekanizması elde edilmektedir.

\paragraph{Çıktıların normalize edilmesi.}
LLM yanıtı doğrudan kullanılmaz; çeşitli normalizasyon adımlarından geçirilir. Tekrarlı maddeler kaldırılır, tarihler standart biçime çevrilir, öncelik değerleri doğrulanır, aksiyon maddelerine kararlı kimlikler atanır ve özet alanları temizlenir. Ayrıca ön yüz veri modeli ile uyum sağlamak amacıyla aksiyon maddelerinin kimlikleri ve atanan kişi alanları slug tabanlı biçime dönüştürülür. Bu yapılandırılmış çıktı daha sonra hem dosya sistemine hem de oturum durumuna yazılır.

\section{Sistem Yazılımı}
\label{sec:sistem_yazilimi}

Bu alt bölümde önerilen mimarinin yazılım düzeyindeki karşılığı açıklanmaktadır. Buradaki amaç, kavramsal mimarinin hangi servisler, veri yapıları ve dosya çıktıları ile gerçekleştirildiğini göstermektir.

\subsection{Arka Uç Servisleri}

Arka uç uygulaması FastAPI tabanlıdır ve servisler yönlendirici mantığı üzerinden bölünmüştür. Oturum yönetimi için \texttt{/api/sessions}, LiveKit işlemleri için \texttt{/api/livekit}, toplantı planlama için \texttt{/api/meetings}, katılımcı işlemleri için \texttt{/api/participants}, kayıt işlemleri için \texttt{/api/recordings} ve yardımcı veri işlemleri için ek yönlendiriciler tanımlanmıştır. Sağlık denetimi uç noktası sistemin erişilebilirliğini ve LiveKit bağlantı durumunu rapor etmektedir.

Toplantıya katılım akışı yazılım düzeyinde şu sırayı izlemektedir:
\begin{enumerate}
\item toplantı için uygulama düzeyinde oturum oluşturulur,
\item LiveKit odası hazırlanır,
\item katılımcı için benzersiz kimlik ve erişim belirteci üretilir,
\item istemci odaya bağlanır,
\item bağlantı ve stream bilgisi arka uca kaydedilir,
\item mikrofon track'i yayınlandığında egress süreci başlatılır,
\item toplantı kapandığında analiz katmanı tetiklenir.
\end{enumerate}

\subsection{Konuşma Analizi ve AI Analizi Çıktıları}

Konuşma analizi tamamlandığında sistem aşağıdaki dosyaları üretmektedir:
\begin{itemize}
\item \texttt{analysis/speech\_segments.json},
\item \texttt{analysis/speakers.rttm}.
\end{itemize}

AI analizi tamamlandığında ise aşağıdaki dosyalar oluşturulmaktadır:
\begin{itemize}
\item \texttt{analysis/ai/transcript.json},
\item \texttt{analysis/ai/summary.json}.
\end{itemize}

Bu dosyalar yalnızca arşivleme amacıyla değil, arayüzün ve sonraki işleme adımlarının veri kaynağı olarak kullanılmaktadır. Ayrıca her analiz aşaması için \texttt{pending}, \texttt{processing}, \texttt{ready} ve \texttt{failed} gibi durum alanları tutularak süreç izlenebilir hale getirilmektedir.

\subsection{Ön Yüz ve Dashboard Yazılımı}

Ön yüz React tabanlıdır ve canlı toplantı ile toplantı sonrası analiz deneyimini aynı uygulama içinde sunmaktadır. Canlı toplantı odasında LiveKit istemcisi üzerinden katılımcı akışları, aktif konuşmacı bilgisi, mikrofon ve kamera durumu ile yeniden bağlanma olayları yönetilmektedir. Toplantı detay ekranında ise aşağıdaki alanlar gösterilmektedir:
\begin{itemize}
\item kayıt durumu,
\item konuşma analizi durumu,
\item AI analiz durumu,
\item yönetici özeti,
\item kararlar,
\item konu etiketleri,
\item aksiyon maddeleri,
\item konuşma zaman çizelgesi,
\item katılımcı bazlı konuşma dağılımı,
\item tam transkript.
\end{itemize}

Bu yapı, arka uçta üretilen yapılandırılmış alanların kullanıcı arayüzüne doğrudan aktarılmasını mümkün kılmaktadır. Dolayısıyla ön yüz, sistem mimarisinin son aşaması olup analitik çıktının görünür temsilidir.

\subsection{Dağıtım ve Yardımcı Bileşenler}

Sistem tek süreçli bir prototip olarak değil, dağıtık servislerden oluşan bir uygulama olarak tasarlanmıştır. Çalışan mimaride aşağıdaki servisler birlikte yer almaktadır:
\begin{itemize}
\item \texttt{livekit},
\item \texttt{egress},
\item \texttt{coturn},
\item \texttt{redis},
\item \texttt{backend},
\item \texttt{celery\_worker},
\item \texttt{celery\_beat},
\item \texttt{gateway}.
\end{itemize}

Bu yapı, medya yönlendirme, kayıt üretme, API işleme ve arka plan görevlerini birbirinden ayırarak sistemin daha sürdürülebilir biçimde yönetilmesini sağlamaktadır. Kod tabanında ayrıca Celery tabanlı deneysel bir \texttt{process\_audio} görevi de bulunmaktadır; ancak ana ürün hattında asıl belirleyici akış, LiveKit track egress ile başlayan ve konuşma analizi ile AI analiz servisleri üzerinden devam eden iş akışıdır.

\subsection{Yöntemin Değerlendirme Açısından Önemi}

Önerilen mimari, değerlendirme açısından iki önemli avantaj sunmaktadır. Birincisi, konuşmacı ayrımının mimari düzeyde korunması sayesinde konuşma çözümleme çıktıları daha doğrudan ve yorumlanabilir hale gelmektedir. İkincisi, semantik analiz katmanının görev ayrımlı olması sayesinde özetleme ve aksiyon çıkarımı gibi işlemler ayrı ayrı doğrulanabilmektedir. Bu yapı, toplantı analizi sistemlerini yalnızca WER veya DER gibi sinyal-seviye ölçütlerle değil, karar kalitesi ve görev kullanılabilirliği bakımından da değerlendirmeye elverişli hale getirmektedir.

\section{Yöntemin Sınırlılıkları}
\label{sec:yontem_sinirliliklari}

Her ne kadar önerilen mimari önemli avantajlar sunsa da bazı sınırlılıklar içermektedir. İlk olarak çok kanallı enerji tabanlı VAD yaklaşımı güçlü olmakla birlikte yoğun ortam gürültüsü ve ciddi mikrofon sızıntısı altında hatalı segment sınırları üretebilir. İkinci olarak ayrı kanal varsayımı çok güçlü bir ön bilgidir; bu varsayımın bozulduğu senaryolarda sistemin avantajı azalabilir. Üçüncü olarak LLM tabanlı özetleme ve aksiyon çıkarımı yapılandırılmış kurallarla sınırlandırılmış olsa da anlamsal hata riskini tamamen ortadan kaldırmaz. Son olarak mevcut ürün çekirdeğinde daha olgun olan yol toplantı sonu analiz hattıdır; tam gerçek zamanlı semantik analiz gelecek geliştirmeler için açık bir araştırma yönü olarak durmaktadır.

## 8. Bölüm 4: Bulgular ve Değerlendirme İçin Güvenli Yazım İskeleti

Bu bölümde sayı uydurulmamalıdır. Aşağıdaki iskelet, gerçek deney sonuçları eklendiğinde doğrudan kullanılabilir.

### 8.1 Değerlendirme Düzeni

Sistem iki ayrı eksende değerlendirilmiştir:

1. Medya ve konuşma çözümleme başarımı
2. Toplantı sonrası anlamsal çıktı kalitesi

Konuşma çözümleme tarafında AMI Meeting Corpus içindeki bireysel mikrofon kayıtları ve proje kapsamında oluşturulan Türkçe toplantı örnekleri kullanılmıştır [8]. Anlamsal çıktı tarafında ise toplantı özetleri, karar listeleri ve aksiyon maddeleri uzman incelemesiyle değerlendirilmiştir.

### 8.2 Yazılabilecek Bulgular

Gerçek ölçüm sonrası aşağıdaki türden cümleler kullanılabilir:

- Katılımcı başına ayrı iz kaydı kullanılması, konuşmacı kimliğinin segment düzeyinde korunmasını kolaylaştırmıştır.
- Overlap bölgelerinde bleed suppression ve dominant-only baskılama mekanizmaları, sahte eşzamanlı konuşma tespitlerini azaltmıştır.
- RTTM çıktıları ve konuşma zaman çizelgesi, toplantı akışının görsel ve nicel olarak incelenmesine olanak vermiştir.
- LangGraph tabanlı görev ayrımı, özetleme ve aksiyon çıkarımı çıktılarının ayrı ayrı denetlenmesini kolaylaştırmıştır.
- Yapılandırılmış JSON çıktıları, toplantı sonrası arayüz entegrasyonunu belirgin biçimde sadeleştirmiştir.

### 8.3 Tablo Önerileri

Teze eklenebilecek tablo başlıkları:

- Tablo 4.1: Veri toplama ve kayıt başarı oranı
- Tablo 4.2: Konuşma analizi metrikleri
- Tablo 4.3: Katılımcı bazlı konuşma süreleri
- Tablo 4.4: Özetleme kalitesi uzman değerlendirmesi
- Tablo 4.5: Aksiyon maddesi çıkarımı doğruluk ve gözden geçirme oranı

### 8.4 Dürüst Sonuç Yazımı

Eğer gerçek deneylerde bazı sonuçlar karışıksa şu dil kullanılmalıdır:

"Sistem, katılımcı bazlı medya toplama ve konuşma zaman çizelgesi üretiminde kararlı sonuçlar vermiştir. Bununla birlikte yoğun örtüşen konuşma ve yüksek kanal sızıntısı içeren senaryolarda segment sınırlarının hassasiyeti düşmüştür. Benzer şekilde, LLM tabanlı aksiyon çıkarımı açık görev ifadelerinde daha güvenilir çalışırken, örtük ya da bağlam bağımlı görevlerde insan gözden geçirmesi gerektirmiştir."

## 9. Bölüm 5: Sonuç

Bu tezde, çevrim içi toplantıların yalnızca iletişim ortamı olarak değil, analiz edilebilir ve kurumsal hafızaya dönüştürülebilir veri kaynakları olarak ele alınmasını sağlayan bütünleşik bir mimari sunulmuştur. Çalışmanın en önemli yönü, konuşmacı ayrımını toplantı sonrasında çözülecek tek kanallı bir tahmin problemi olmaktan çıkarıp, bireysel ses izlerinin toplandığı medya düzeyine yerleştirmesidir. Bu sayede konuşma çözümleme, toplantı özeti ve aksiyon maddesi çıkarımı gibi üst katman görevleri daha sağlam bir veri temeli üzerinde yürütülebilmiştir.

LiveKit tabanlı medya mimarisi, oda yönetimi, webhook tabanlı olay takibi ve track-level kayıt yapısıyla sistemin veri edinim temelini oluşturmaktadır. LangGraph ise toplantı sonrası semantik analiz akışının açıkça tanımlanmış orkestrasyon omurgasını temsil etmiş; toplantı analizini transkripsiyon, özetleme ve aksiyon çıkarımı olarak ayrışan ama ortak durum paylaşan görevler halinde modellemeyi mümkün kılmıştır. Sonuç olarak çalışma, medya katmanı ile semantik ajan katmanını aynı çatı altında birleştirerek akıllı toplantı analizi için modüler ve savunulabilir bir tez omurgası ortaya koymuştur.

Gelecek çalışmalarda gerçek zamanlı konuşma analizi, daha gelişmiş overlap modelleme, insan geri bildirimiyle iyileştirilen ajan akışları ve duygu analizi gibi ek semantik katmanlar sisteme entegre edilebilir. Ancak mevcut sürümün ana bilimsel değeri, LiveKit tabanlı çok kanallı veri edinimi ile LangGraph tabanlı ajan orkestrasyonunu çalışan bir toplantı platformunda bir araya getirmesidir.

## 10. Şekil ve Diyagram Önerileri

Teze eklenmesi faydalı olacak şekiller:

1. Genel sistem mimarisi: Frontend, FastAPI, LiveKit, Egress, SessionStore, SpeechAnalysisService, LangGraph ajan katmanı
2. Toplantı başlatma ve token üretim akışı
3. Track publish -> webhook -> egress -> recording file akışı
4. Çok kanallı hizalama ve VAD segment üretim şeması
5. LangGraph ajan grafı

LangGraph ajan grafı için önerilen şema:

`START -> Transcription Agent -> {Summary Agent, Action Item Agent} -> END`

## 11. Kaynakça İçin Korunacak ve Eklenecek Kaynak Havuzu

Bu bölüm, mevcut tezdeki kaynakları korumak ve kullanım yerlerini netleştirmek için iki katmanda düzenlenmiştir. İlk katmanda güncel mimariyle doğrudan ilişkili çekirdek ve bağlamsal kaynaklar yer alır. İkinci katmanda ise mevcut tezden korunabilecek ve ilgili çalışmalar bölümünde kullanılabilecek geniş kaynak havuzu tutulur.

### 11.1 Çekirdek Güncel ve Bağlamsal Kaynaklar

[1] LiveKit Documentation, "Client Protocol." https://docs.livekit.io/reference/internals/client-protocol/

[2] LiveKit Documentation, "Webhooks & events." https://docs.livekit.io/intro/basics/rooms-participants-tracks/webhooks-events/

[3] LiveKit Documentation, "Track egress." https://docs.livekit.io/transport/media/ingress-egress/egress/track/

[4] OpenVidu Documentation, "Recording." https://docs.openvidu.io/en/stable/advanced-features/recording/

[5] A. Radford, J. W. Kim, T. Xu, G. Brockman, C. McLeavey and I. Sutskever, "Robust Speech Recognition via Large-Scale Weak Supervision," arXiv:2212.04356, 2022. https://arxiv.org/abs/2212.04356

[6] SYSTRAN, "faster-whisper." https://github.com/SYSTRAN/faster-whisper

[7] H. Bredin et al., "pyannote.audio: Neural Building Blocks for Speaker Diarization," ICASSP 2020. https://resourcecenter.ieee.org/conferences/icassp-2020/spsicassp20vid0175

[8] J. Carletta et al., "The AMI Meeting Corpus: A Pre-announcement," MLMI 2005 / Springer, 2006. https://www.research.ed.ac.uk/en/publications/the-ami-meeting-corpus-a-pre-announcement

[9] V. Rennard, G. Shang, J. Hunter and M. Vazirgiannis, "Abstractive Meeting Summarization: A Survey," Transactions of the Association for Computational Linguistics, vol. 11, 2023. https://aclanthology.org/2023.tacl-1.49/

[10] S. Asthana, S. Hilleli, P. He and A. Halfaker, "Summaries, Highlights, and Action Items: Design, Implementation and Evaluation of an LLM-powered Meeting Recap System." https://www.microsoft.com/en-us/research/publication/summaries-highlights-and-action-items-design-implementation-and-evaluation-of-an-llm-powered-meeting-recap-system/

[11] P. N. Bennett and J. G. Carbonell, "Combining Probability-Based Rankers for Action-Item Detection," NAACL 2007. https://aclanthology.org/N07-1041/

[12] J. Liu, C. Deng, Q. Zhang, Q. Chen and W. Wang, "Meeting Action Item Detection with Regularized Context Modeling," ICASSP 2023. https://resourcecenter.ieee.org/conferences/icassp-2023/spsicassp23vid1592

[13] LangChain, "LangGraph overview." https://docs.langchain.com/oss/python/langgraph/overview

[14] LangChain Reference, "StateGraph." https://reference.langchain.com/python/langgraph/graph/state/StateGraph

### 11.2 Mevcut Tezden Korunabilecek Kaynaklar

- B. Chen et al., "Scalable Multi-Robot Collaboration with LLMs: CMAS vs DMAS," arXiv preprint, 2024.
- M. Helmi, "Modeling Response Consistency in Multi-Agent LLM Systems," International Journal of Multi-Agent Systems (IJMAS), 2025.
- A. Asha, "Automatic Meeting Minutes Generation," Journal of AI Research & Applications, 2025.
- D. Raj et al., "Integration of Speech Separation, Diarization, and Recognition," IEEE/ACM Transactions on Audio, Speech, and Language Processing (TASLP), 2021.
- A. Senthilselvi et al., "Real-Time Smart Meeting Assistant using Edge AI for Audio Capture, Speech-to-Text Conversion, and Meeting Scheduling," Proceedings of the International Conference on Computing and Data Science (ICCDS), 2025.
- H. Bredin et al., "pyannote.audio: Neural Building Blocks for Speaker Diarization," ICASSP, 2020.
- A. Plaquet and H. Bredin, "Powerset Multi-Class Cross Entropy Loss for Neural Speaker Diarization," arXiv:2310.13025, 2023.
- L. Lanzendörfer et al., "Benchmarking Diarization Models," Journal of Speech Technology, 2025.
- D. O'Shaughnessy, "Speaker Diarization: A Review," Applied Sciences, 2025.
- S. Serafini et al., "An Experimental Review of Speaker Diarization Methods," ICASSP, 2023.
- A. Meise et al., "Loose Coupling of Spectral and Spatial Models for Multi-Channel Diarization and Enhancement of Meetings in Dynamic Environments," arXiv preprint, 2026.
- H. Yin et al., "SpeakerLM: End-to-End Versatile Speaker Diarization and Recognition with Multimodal Large Language Models," AAAI, 2026.
- R. Pacheco et al., "SDBench: A Comprehensive Benchmark Suite for Speaker Diarization," arXiv preprint, 2025.
- I. McCowan et al., "The AMI Meeting Corpus," Proceedings of Measuring Behavior 2005, 2005.
- S. Asthana et al., "Summaries, Highlights, and Action Items," Proceedings of the ACM on Human-Computer Interaction (CSCW), 2025.
- V. Rennard et al., "Abstractive Meeting Summarization: A Survey," Transactions of the Association for Computational Linguistics (TACL), 2023.
- S. Huang et al., "Automatic Meeting Summarization and Topic Detection," IEEE Conference, 2018.
- F. Kirstein et al., "Tell Me What I Need to Know: RAG in Meeting Analysis," NLP Conference Proceedings, 2024.
- A. Baeuerle et al., "AutoMeet: Automated Meeting Summarization," arXiv preprint, 2025.
- T. Thonet, L. Besacier and J. Rozen, "ELITR-Bench: A Meeting Assistant Benchmark for Long-Context Language Models," COLING 2025, 2025.
- bidkar2024, "Meeting Summarization: A Survey," IJRASET, 2024.
- Y. Hu et al., "Meeting Delegate: Intelligent Task Assignment and Notification," Microsoft Research / arXiv, 2025.
- T. Wijerathne et al., "ScheduleMe: Multi-Agent Calendar Assistant," International Conference on Intelligent Agents (ICIA), 2025.
- B. Varjú and B. Varga, "Multi-Agent LLM System for Meeting Info Processing," IEEE Conference, 2025.
- G. Tür et al., "The CALO Meeting Assistant System," IEEE Transactions on Audio, Speech, and Language Processing (TASLP), 2010.

## 12. Koddaki Karşılıklar

Tezde anlatılan bileşenlerin koddaki temel karşılıkları aşağıdadır:

- LiveKit servis katmanı: `meeting_analyzer/src/services/livekit_service.py`
- Egress ve kayıt yaşam döngüsü: `meeting_analyzer/src/services/egress_recording_service.py`
- Oturum durumu: `meeting_analyzer/src/services/session_store.py`
- Toplantı verisi: `meeting_analyzer/src/services/meeting_store.py`
- Çok kanallı konuşma analizi: `meeting_analyzer/src/services/speech_analysis_service.py`
- VAD ve RTTM çekirdeği: `meeting_analyzer/module1_vad/`
- AI analizi: `meeting_analyzer/src/services/ai_analysis_service.py`
- LangGraph ajan grafı: `agents/services/meeting_graph.py`
- Özetleme ajanı: `agents/services/summary_agent.py`
- Aksiyon ajanı: `agents/services/action_item_agent.py`
- Canlı toplantı istemcisi: `frontend/src/app/livekit-meeting/hooks/useMeeting.ts`
- Toplantı odası arayüzü: `frontend/src/app/pages/LiveKitMeetingRoom.tsx`
- Toplantı sonrası analiz ekranı: `frontend/src/app/pages/MeetingDetail.tsx`

## 13. Sonraki Düzenleme Adımı

Bu taslak temel alınarak ikinci aşamada şu işlemler yapılabilir:

1. Üniversite şablonuna göre Word veya LaTeX biçimine çevrilmesi
2. Şekillerin ve sistem diyagramlarının çizilmesi
3. Bulgular bölümünün gerçek deney sonuçlarıyla doldurulması
4. Kaynakça biçiminin IEEE, APA veya üniversite şablonuna göre normalize edilmesi
