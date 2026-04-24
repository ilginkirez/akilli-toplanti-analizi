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
    should_mark_for_review,
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
- assignee sadece transcriptte aciksa yaz; degilse bos string don.
- due_date sadece transcriptte acik ve kesin bir takvim tarihi varsa doldur.
- Goreli tarih ifadelerini takvim tarihine cevirme: yarin, haftaya, cuma, ay sonu gibi ifadelerde due_date bos string olsun.
- meeting_date bilgisinden tarih turetme.
- priority sadece transcriptte net bicimde anlasiliyorsa doldur; aksi halde bos string don.
- Confidence 0.0 ile 1.0 arasinda olsun.
- Confidence 0.65'ten kucukse needs_review true olsun, degilse false olsun.
- Type alani sadece su degerlerden biri olsun: direct, volunteer, implicit, conditional, group.
- direct: gorev bir kisiye dogrudan verildi.
- volunteer: kisi gorevi kendi ustlendi.
- implicit: yapilacak is var ama atama veya talimat dolayli.
- conditional: gorev bir kosula bagli.
- group: gorev ekip ya da grup icin ortak.
- Yorum, tahmin veya baglamdan cikarimla yeni detay ekleme.
- JSON disinda hicbir metin yazma.

Beklenen JSON:
{
  "action_items": [
    {
      "task": "string",
      "assignee": "string",
      "due_date": "YYYY-MM-DD veya bos string",
      "priority": "low|medium|high|critical veya bos string",
      "confidence": 0.0,
      "type": "direct|volunteer|implicit|conditional|group",
      "needs_review": true
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

    if not transcript.strip():
        return {"action_items": []}

    result = service._llm().complete_json(
        system_prompt=ACTION_ITEM_SYSTEM_PROMPT,
        user_prompt=json.dumps(
            {
                "meeting_date": meeting_date,
                "segments": segments[:120],
                "transcript": transcript[:12000],
            },
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
        normalized = {
            "task": normalize_text(item.get("task", "")),
            "assignee": normalize_text(item.get("assignee", ""), max_length=80),
            "due_date": normalize_due_date(str(item.get("due_date", "")).strip()),
            "priority": normalize_priority(item.get("priority", "")),
            "confidence": confidence,
            "type": normalize_action_item_type(item.get("type", "")),
        }

        if not normalized["task"]:
            continue

        dedupe_key = (
            normalized["task"].casefold(),
            normalized["assignee"].casefold(),
            normalized["due_date"],
        )
        if dedupe_key in seen:
            continue

        seen.add(dedupe_key)
        normalized["needs_review"] = should_mark_for_review(item, confidence)
        tasks.append(normalized)

    return {"action_items": tasks}
