import json
from typing import Any
from .context import AnalysisAgentService
from .state import MeetingAnalysisState
from .utils import (
    normalize_confidence,
    normalize_text,
    normalize_due_date,
    normalize_priority,
    normalize_action_item_type,
    normalize_user_id,
    normalize_candidates,
    should_mark_for_review,
    deduplicate_tasks,
)

ACTION_ITEM_SYSTEM_PROMPT = """
Sen bir toplanti aksiyon maddesi cikarma ajanisin.
Sadece verilen transcript ve segmentlerde acikca gecen veya guclu bicimde desteklenen gorevleri cikar.
Tum ciktilar Turkce olsun.
Uydurma gorev, kisi, oncelik veya tarih ekleme.
Eger acik gorev yoksa bos liste don.
Her zaman gecerli JSON don.
Tum alanlar her zaman mevcut olsun.

Kurallar:
- Her action item kisa, net ve uygulanabilir olsun.
- Ayni gorevi farkli sekilde tekrar etme.
- due_date: Transcriptte kesin bir takvim tarihi varsa dogrudan YYYY-MM-DD formatinda yaz.
  Transcriptte goreli bir tarih ifadesi varsa (yarin, haftaya, gelecek pazartesi, cuma, ay sonu, 3 gun icinde vb.)
  meeting_date degerini referans alarak hesapla ve YYYY-MM-DD formatinda yaz.
  Ornegin meeting_date "2026-04-25" ise ve konusmaci "yarin" diyorsa due_date "2026-04-26" olur.
  Eger ne kesin ne de goreli bir tarih yoksa bos string don.
- priority sadece transcriptte net bicimde anlasiliyorsa doldur; aksi halde bos string don.
- Confidence 0.0 ile 1.0 arasinda olsun.
- Confidence 0.65'ten kucukse needs_review true olsun, degilse false olsun.
- Type alani sadece su degerlerden biri olsun: direct, volunteer, implicit, conditional, group.
  - direct: gorev bir kisiye dogrudan verildi.
  - volunteer: kisi gorevi kendi ustlendi.
  - implicit: yapilacak is var ama atama veya talimat dolayli.
  - conditional: gorev bir kosula bagli.
  - group: gorev ekip ya da grup icin ortak.
- Transcript'in TAMAMINI oku. Bas, orta ve son kisimlardan gorev cikar.
- Yorum, tahmin veya baglamdan cikarimla yeni detay ekleme.
- JSON disinda hicbir metin yazma.

GOREV ATAMA KURALLARI (cok onemli):
- Sana bir katilimci listesi (participants) verilecek. Her katilimcinin user_id ve name alani var.
- Gorev birine ataniyorsa, assigned_to_user_id alanina o kisinin user_id degerini yaz.
- assignee_name alanina o kisinin adini yaz.
- Eger transcriptte gorev kime ait oldugu acik degilse assigned_to_user_id = null, assignee_name = null yaz.
- Eger birden fazla katilimci ayni ada sahipse veya atama belirsizse:
  - assigned_to_user_id = null
  - ambiguous = true
  - candidates listesine olasi user_id'leri yaz
  - reason alanina belirsizlik sebebini yaz
- Eger gorev net olarak tek kisiye atanabiliyorsa ambiguous = false, candidates = [] olsun.
- Katilimci listesinde olmayan bir kisiye gorev atama. assigned_to_user_id sadece verilen user_id'lerden biri olabilir.
- Eger transcriptte gecen isim katilimci listesindeki hicbir kisiyle eslesemiyorsa assigned_to_user_id = null yaz.

KAYNAK REFERANSI KURALLARI:
- Her gorev icin source_quote alanina, transcript'ten o gorevi destekleyen KISA bir alinti yaz (en fazla 1-2 cumle).
- Alinti birebir transcript'ten alinmali, degistirilmemeli.
- source_speaker alanina, o gorev hakkinda konusan kisinin adini yaz.
- Eger alinti yapilamiyorsa source_quote = "", source_speaker = "" olsun.

BIRLESIK GOREV KURALLARI:
- Eger bir cumlede birden fazla bagimsiz is varsa (ornegin "Raporu hazirla ve musteriye gonder"),
  bunlari ayri action item'lara bol.
- Ancak mantiksal olarak tek bir gorev olan ifadeleri bolme (ornegin "Sunum dosyasini guncelle").

OZET BAGLAMI:
- Sana toplantinin ozeti ve alinmis kararlar da verilecek (eger mevcutsa).
- Bu bilgileri gorevlerin baglamini anlamak icin kullan.
- Kararlarla tutarli gorevler cikar.
- Ancak ozetten yeni gorev uretme; gorevler yalnizca transcript'ten cikarilmali.

Ornek cikti:
{
  "action_items": [
    {
      "task": "Kullanici arayuzu tasarimini guncelle",
      "assigned_to_user_id": "usr-abc12345",
      "assignee_name": "Ahmet Yilmaz",
      "due_date": "2026-04-28",
      "priority": "high",
      "confidence": 0.92,
      "type": "direct",
      "needs_review": false,
      "ambiguous": false,
      "candidates": [],
      "reason": "",
      "source_quote": "Ahmet, arayuzu cuma gününe kadar guncelle",
      "source_speaker": "Mehmet"
    },
    {
      "task": "Haftalik raporu hazirla",
      "assigned_to_user_id": null,
      "assignee_name": null,
      "due_date": "",
      "priority": "",
      "confidence": 0.70,
      "type": "implicit",
      "needs_review": false,
      "ambiguous": true,
      "candidates": ["usr-abc12345", "usr-def67890"],
      "reason": "Transcriptte raporu kimin hazirlayacagi net belirtilmemis",
      "source_quote": "haftalik rapor hazirlanmali",
      "source_speaker": "Zeynep"
    }
  ]
}

Beklenen JSON:
{
  "action_items": [
    {
      "task": "string",
      "assigned_to_user_id": "string veya null",
      "assignee_name": "string veya null",
      "due_date": "YYYY-MM-DD veya bos string",
      "priority": "low|medium|high|critical veya bos string",
      "confidence": 0.0,
      "type": "direct|volunteer|implicit|conditional|group",
      "needs_review": true,
      "ambiguous": false,
      "candidates": [],
      "reason": "",
      "source_quote": "string veya bos string",
      "source_speaker": "string veya bos string"
    }
  ]
}
""".strip()

def run_action_item_agent(
    service: AnalysisAgentService,
    state: MeetingAnalysisState,
) -> MeetingAnalysisState:
    transcript = state.get("full_text", "")
    segments = state.get("transcript_segments", [])
    meeting_date = state.get("meeting_date", "")
    meeting_participants = state.get("meeting_participants", [])
    summary_result = state.get("summary_result") or {}

    if not transcript.strip():
        return {"action_items": []}

    # Katılımcı listesini LLM'e gönderilecek formata dönüştür
    participants_for_llm = [
        {"user_id": p.get("user_id"), "name": p.get("name", "")}
        for p in meeting_participants
        if p.get("user_id") and p.get("name")
    ]

    # Geçerli user_id seti (normalizasyon için)
    valid_user_ids = {p["user_id"] for p in participants_for_llm}

    # Summary bağlamını hazırla (summary-aware extraction)
    summary_context = {}
    if summary_result:
        exec_summary = summary_result.get("executiveSummary", "")
        key_decisions = summary_result.get("keyDecisions", [])
        if exec_summary or key_decisions:
            summary_context = {
                "meeting_summary": exec_summary,
                "key_decisions": key_decisions,
            }

    user_prompt_data: dict[str, Any] = {
        "meeting_date": meeting_date,
        "participants": participants_for_llm,
        "segments": segments[:1500],
        "transcript": transcript[:150000],
    }
    if summary_context:
        user_prompt_data["summary_context"] = summary_context

    result = service._llm().complete_json(
        system_prompt=ACTION_ITEM_SYSTEM_PROMPT,
        user_prompt=json.dumps(
            user_prompt_data,
            ensure_ascii=False,
            indent=2,
        ),
        temperature=0.1,
    )

    tasks: list[dict[str, Any]] = []
    seen = set()

    for item in result.get("action_items", []):
        if not isinstance(item, dict):
            continue

        confidence = normalize_confidence(item.get("confidence", 0.0))
        raw_user_id = normalize_user_id(
            item.get("assigned_to_user_id"), valid_user_ids
        )
        raw_candidates = normalize_candidates(
            item.get("candidates", []), valid_user_ids
        )
        raw_ambiguous = bool(item.get("ambiguous", False))

        # LLM geçersiz user_id döndüyse → ambiguous yap
        if item.get("assigned_to_user_id") and raw_user_id is None:
            raw_ambiguous = True
            raw_user_id = None

        normalized = {
            "task": normalize_text(item.get("task", "")),
            "assigned_to_user_id": raw_user_id,
            "assignee_name": normalize_text(
                item.get("assignee_name", ""), max_length=80
            ),
            "due_date": normalize_due_date(str(item.get("due_date", "")).strip()),
            "priority": normalize_priority(item.get("priority", "")),
            "confidence": confidence,
            "type": normalize_action_item_type(item.get("type", "")),
            "ambiguous": raw_ambiguous,
            "candidates": raw_candidates,
            "reason": normalize_text(item.get("reason", ""), max_length=200),
            "source_quote": normalize_text(
                item.get("source_quote", ""), max_length=300
            ),
            "source_speaker": normalize_text(
                item.get("source_speaker", ""), max_length=80
            ),
        }

        if not normalized["task"]:
            continue

        # Basit tam-eşleşme dedup (aynı task+user+date → atla)
        dedupe_key = (
            normalized["task"].casefold(),
            normalized["assigned_to_user_id"] or "",
            normalized["due_date"],
        )
        if dedupe_key in seen:
            continue

        seen.add(dedupe_key)
        normalized["needs_review"] = should_mark_for_review(item, confidence)
        tasks.append(normalized)

    # Akıllı dedup: Jaccard benzerliğiyle aynı kişiye atanan benzer görevleri birleştir
    tasks = deduplicate_tasks(tasks)

    return {"action_items": tasks}
