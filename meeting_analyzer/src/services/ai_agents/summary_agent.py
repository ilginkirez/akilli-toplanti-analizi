import json
from .context import AnalysisAgentService
from .state import MeetingAnalysisState
from .utils import (
    normalize_summary_text,
    normalize_string_list,
    MAX_DECISIONS,
    MAX_TOPICS,
)

SUMMARY_SYSTEM_PROMPT = """
Sen bir toplanti ozetleme ajanisin.
Sadece verilen transcript ve segmentlere dayan.
Tum ciktilar Turkce olsun.
Uydurma bilgi, yorum veya transcriptte gecmeyen karar ekleme.
Her zaman gecerli JSON don.
Tum alanlar her zaman mevcut olsun.

Kurallar:
- Sadece transcriptte acikca gecen bilgiye dayan.
- executiveSummary 2 ila 4 cumle olsun; kisa, yogun ve yonetici seviyesi bir ozet yaz.
- executiveSummary icine yeni karar, gorev veya tarih uydurma.
- keyDecisions yalnizca toplantida acikca alinmis kararlar icersin.
- Acik karar yoksa keyDecisions bos liste olsun.
- topics sadece ana konulari icersin; kisa basliklar kullan.
- topics en fazla 5 madde olsun.
- Tekrar eden veya anlami ayni olan maddeleri birlestir.
- Belirsiz, varsayimsal veya yoruma dayali madde ekleme.
- JSON disinda hicbir metin yazma.

Beklenen JSON:
{
  "executiveSummary": "2-4 cumlelik yonetici ozeti",
  "keyDecisions": ["karar 1", "karar 2"],
  "topics": ["konu 1", "konu 2"]
}
""".strip()

def run_summary_agent(
    service: AnalysisAgentService,
    state: MeetingAnalysisState,
) -> MeetingAnalysisState:
    transcript = state.get("full_text", "")
    segments = state.get("transcript_segments", [])
    
    if not transcript.strip():
        return {
            "summary_result": {
                "executiveSummary": "",
                "keyDecisions": [],
                "topics": [],
            }
        }

    result = service._llm().complete_json(
        system_prompt=SUMMARY_SYSTEM_PROMPT,
        user_prompt=json.dumps(
            {
                "segments": segments[:120],
                "transcript": transcript[:12000],
            },
            ensure_ascii=False,
            indent=2,
        ),
        temperature=0.1,
    )

    executive_summary = str(
        result.get("executiveSummary")
        or result.get("highlights_summary")
        or ""
    ).strip()

    key_decisions = result.get("keyDecisions")
    if not isinstance(key_decisions, list):
        minutes = result.get("hierarchical_minutes") or {}
        key_decisions = minutes.get("decisions", [])

    topics = result.get("topics")
    if not isinstance(topics, list):
        minutes = result.get("hierarchical_minutes") or {}
        topics = minutes.get("topics", [])

    summary_result = {
        "executiveSummary": normalize_summary_text(executive_summary),
        "keyDecisions": normalize_string_list(
            key_decisions,
            limit=MAX_DECISIONS,
        ),
        "topics": normalize_string_list(
            topics,
            limit=MAX_TOPICS,
            max_item_length=80,
        ),
    }

    return {"summary_result": summary_result}
