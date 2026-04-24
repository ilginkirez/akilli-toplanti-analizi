"""
test_action_item_agent_only.py
------------------------------
Action item agent'inin iyilestirilmis prompt'unu dogrudan test eder.
LangGraph pipeline'ina dokunmaz — sadece GroqLLM + yeni prompt ile
mevcut transcript verisini kullanarak aksiyon maddesi cikarir.

Gereksinimler:
  - GROQ_API_KEY env degiskeni tanimli olmali

Calistirma:
  cd meeting_analyzer
  python tests/test_action_item_agent_only.py
"""

import json
import os
import sys
import time
from pathlib import Path

# --- Proje kokunu path'e ekle ------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# --- Mevcut test sonucunu bul -------------------------------------------------
BUNDLE_ROOT = (
    PROJECT_ROOT.parent
    / "sesKaydı"
    / "meeting_pull_20260424_oracle"
    / "bundles"
    / "deneme__meet-m-eb2b7632"
)
LANGGRAPH_RESULT = BUNDLE_ROOT / "langgraph_test_result.json"


def _load_transcript_data() -> tuple[list[dict], str, str]:
    """Onceki pipeline sonucundan transcript verilerini yukle."""
    if LANGGRAPH_RESULT.exists():
        data = json.loads(LANGGRAPH_RESULT.read_text(encoding="utf-8"))
        segments = data.get("transcript_segments", [])
        full_text = data.get("full_text", "")
        meeting_date = "2026-04-24"
        print(f"  [OK] Mevcut test sonucu yuklendi: {LANGGRAPH_RESULT.name}")
        print(f"       {len(segments)} segment, {len(full_text)} karakter")
        return segments, full_text, meeting_date

    # Fallback: ornek transcript verisi
    print("  [!] Mevcut test sonucu bulunamadi, ornek veri kullaniliyor")
    segments = [
        {"speaker": "Merve Çatalkaya", "participant_id": "par_697f47",
         "start": 23.61, "end": 34.56,
         "text": "Merhaba Ilgın, nasılsın? Son metriklere baktım, fark ettin mi? "
                 "Kullanıcı sayısı artıyor ama retention düşüyor. "
                 "Özellikle ilk iki dakikada kayıp çok yüksek."},
        {"speaker": "Ilgın Kirez", "participant_id": "par_937b69",
         "start": 34.56, "end": 36.59,
         "text": "Merve iyiyim. Evet ben de fark ettim."},
        {"speaker": "Ilgın Kirez", "participant_id": "par_937b69",
         "start": 37.19, "end": 41.01,
         "text": "En büyük soru mikrofon izni gibi görünüyor. "
                 "Kullanıcıların çoğu arada takılıyor."},
        {"speaker": "Merve Çatalkaya", "participant_id": "par_697f47",
         "start": 44.76, "end": 46.77,
         "text": "Aynen bu kritik."},
        {"speaker": "Merve Çatalkaya", "participant_id": "par_697f47",
         "start": 47.39, "end": 49.51,
         "text": "Ben onboarding tarafını alıyorum. Yarın ilk prototipi hazırlarım."},
        {"speaker": "Ilgın Kirez", "participant_id": "par_937b69",
         "start": 48.71, "end": 54.01,
         "text": "Tamam. Ben de teknik analiz kısmını haftaya bitireceğim."},
        {"speaker": "Merve Çatalkaya", "participant_id": "par_697f47",
         "start": 54.08, "end": 56.03,
         "text": "Süper. O zaman hızlıca ilerleyelim."},
        {"speaker": "Ilgın Kirez", "participant_id": "par_937b69",
         "start": 56.03, "end": 57.57,
         "text": "Ben analizleri kısa sürede çıkaracağım."},
    ]
    full_text = "\n\n".join(
        f"[{s['speaker']} | {s['start']:.2f}s - {s['end']:.2f}s]\n{s['text']}"
        for s in segments
    )
    meeting_date = "2026-04-25"
    return segments, full_text, meeting_date


def run_test():
    print("=" * 70)
    print("  ACTION ITEM AGENT - IYILESTIRILMIS PROMPT TESTI")
    print("=" * 70)

    # --- API key kontrolu ---
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("\n  [HATA] GROQ_API_KEY env degiskeni tanimli degil!")
        print("  Cozum:  set GROQ_API_KEY=gsk_...")
        sys.exit(1)

    # --- Transcript verilerini yukle ---
    print("\n--- 1) Transcript Verisi Yukleniyor ---")
    segments, full_text, meeting_date = _load_transcript_data()

    # --- GroqLLM client'i olustur ---
    print("\n--- 2) Groq LLM Baglantisi ---")
    from src.services.ai_llm_client import GroqLLM
    llm = GroqLLM()
    print(f"  Model: {llm.model}")

    # --- Yeni prompt'u dosyadan oku (langgraph import zincirini tetiklememek icin) ---
    agent_file = PROJECT_ROOT / "src" / "services" / "ai_agents" / "action_item_agent.py"
    agent_source = agent_file.read_text(encoding="utf-8")
    # ACTION_ITEM_SYSTEM_PROMPT = """...""".strip() seklinde tanimli
    start_marker = 'ACTION_ITEM_SYSTEM_PROMPT = """'
    end_marker = '""".strip()'
    idx_start = agent_source.index(start_marker) + len('ACTION_ITEM_SYSTEM_PROMPT = ')
    idx_end = agent_source.index(end_marker) + len('"""')
    prompt_raw = agent_source[idx_start:idx_end]
    # Python string literal olarak evaluate et
    ACTION_ITEM_SYSTEM_PROMPT = eval(prompt_raw + ".strip()")
    print(f"  Prompt uzunlugu: {len(ACTION_ITEM_SYSTEM_PROMPT)} karakter")

    # --- LLM'e gonder ---
    print(f"\n--- 3) Action Item Cikarma (meeting_date={meeting_date}) ---")
    user_prompt = json.dumps(
        {
            "meeting_date": meeting_date,
            "segments": segments[:1500],
            "transcript": full_text[:150000],
        },
        ensure_ascii=False,
        indent=2,
    )

    t0 = time.perf_counter()
    result = llm.complete_json(
        system_prompt=ACTION_ITEM_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.1,
    )
    elapsed = time.perf_counter() - t0
    print(f"  LLM yanit suresi: {elapsed:.2f}s")

    # --- Normalize et ---
    print(f"\n--- 4) Normalizasyon ---")
    # utils'i dogrudan import et (langgraph zincirini tetiklememek icin)
    import importlib.util
    utils_path = PROJECT_ROOT / "src" / "services" / "ai_agents" / "utils.py"
    spec = importlib.util.spec_from_file_location("ai_agents_utils", str(utils_path))
    utils_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(utils_mod)
    normalize_confidence = utils_mod.normalize_confidence
    normalize_text = utils_mod.normalize_text
    normalize_due_date = utils_mod.normalize_due_date
    normalize_priority = utils_mod.normalize_priority
    normalize_action_item_type = utils_mod.normalize_action_item_type
    should_mark_for_review = utils_mod.should_mark_for_review

    raw_items = result.get("action_items", [])
    print(f"  LLM ham cikti: {len(raw_items)} action item")

    tasks = []
    seen = set()
    for item in raw_items:
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

    # --- Sonuclari goster ---
    print(f"\n{'=' * 70}")
    print(f"  SONUCLAR: {len(tasks)} aksiyon maddesi")
    print(f"{'=' * 70}")

    for i, task in enumerate(tasks, 1):
        print(f"\n  [{i}] {task['task']}")
        print(f"      Atanan:     {task['assignee'] or '(belirsiz)'}")
        print(f"      Tarih:      {task['due_date'] or '(yok)'}")
        print(f"      Oncelik:    {task['priority'] or '(belirsiz)'}")
        print(f"      Tip:        {task['type']}")
        print(f"      Guven:      {task['confidence']}")
        print(f"      Inceleme:   {'Evet' if task['needs_review'] else 'Hayir'}")

    # --- Onemli: due_date iyilestirmesini kontrol et ---
    items_with_date = [t for t in tasks if t["due_date"]]
    items_without_date = [t for t in tasks if not t["due_date"]]

    print(f"\n{'=' * 70}")
    print(f"  IYILESTIRME DEGERLENDIRMESI")
    print(f"{'=' * 70}")
    print(f"  Tarih iceren aksiyonlar:   {len(items_with_date)}")
    print(f"  Tarihsiz aksiyonlar:       {len(items_without_date)}")
    print(f"  Toplam:                    {len(tasks)}")

    if items_with_date:
        print(f"\n  [OK] Goreli tarih cevirmesi CALISIYOR:")
        for t in items_with_date:
            print(f"       -> {t['task'][:50]}  =>  {t['due_date']}")
    else:
        print(f"\n  [!] Hicbir aksiyonda tarih bulunamadi.")
        print(f"      (Bu normal olabilir - transcript'te tarih ifadesi yoksa)")

    # --- JSON olarak kaydet ---
    output_path = PROJECT_ROOT / "tests" / "action_item_test_result.json"
    output_payload = {
        "test_timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "meeting_date": meeting_date,
        "model": llm.model,
        "llm_elapsed_sec": round(elapsed, 2),
        "raw_items_count": len(raw_items),
        "normalized_items_count": len(tasks),
        "action_items": tasks,
        "raw_llm_response": result,
    }
    output_path.write_text(
        json.dumps(output_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\n  Sonuc kaydedildi: {output_path.name}")
    print(f"\n  {'=' * 70}")
    print(f"  TEST TAMAMLANDI")
    print(f"  {'=' * 70}")


if __name__ == "__main__":
    run_test()
