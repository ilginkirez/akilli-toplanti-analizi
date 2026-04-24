"""
test_action_item_relative_dates.py
-----------------------------------
Goreli tarih ifadelerinin (yarin, haftaya, cuma) meeting_date'e
gore YYYY-MM-DD formatina donusturulmesini test eder.

Calistirma:
  cd meeting_analyzer
  python tests/test_action_item_relative_dates.py
"""

import json
import os
import sys
import time
import importlib.util
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def run_test():
    print("=" * 70)
    print("  GORELI TARIH CEVIRME TESTI")
    print("=" * 70)

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("\n  [HATA] GROQ_API_KEY env degiskeni tanimli degil!")
        sys.exit(1)

    from src.services.ai_llm_client import GroqLLM

    # Prompt dosyadan oku
    agent_file = PROJECT_ROOT / "src" / "services" / "ai_agents" / "action_item_agent.py"
    agent_source = agent_file.read_text(encoding="utf-8")
    start_marker = 'ACTION_ITEM_SYSTEM_PROMPT = """'
    end_marker = '""".strip()'
    idx_start = agent_source.index(start_marker) + len('ACTION_ITEM_SYSTEM_PROMPT = ')
    idx_end = agent_source.index(end_marker) + len('"""')
    prompt_raw = agent_source[idx_start:idx_end]
    ACTION_ITEM_SYSTEM_PROMPT = eval(prompt_raw + ".strip()")

    # Tarih ifadesi iceren yapay transcript
    meeting_date = "2026-04-25"

    transcript = (
        "[Merve Catalkaya | 00:01:00 - 00:01:15]\n"
        "Ilgin, mikrofon izni sorununu yarina kadar coz lutfen. Bu cok kritik.\n\n"
        "[Ilgin Kirez | 00:01:15 - 00:01:25]\n"
        "Tamam yarin halledecegim. Ayrica haftaya pazartesiye kadar kullanici analiz raporunu hazirlayabilirim.\n\n"
        "[Merve Catalkaya | 00:01:25 - 00:01:35]\n"
        "Cok iyi. Ben de cuma gunune kadar on-boarding akisini yeniden tasarlayacagim. Bu yuksek oncelikli.\n\n"
        "[Ilgin Kirez | 00:01:35 - 00:01:45]\n"
        "Tamamdir. Eger A/B test sonuclari olumlu gelirse dashboard tasarimini da guncelleriz."
    )

    segments = [
        {"speaker": "Merve Catalkaya", "start": 60, "end": 75,
         "text": "Ilgin, mikrofon izni sorununu yarina kadar coz lutfen. Bu cok kritik."},
        {"speaker": "Ilgin Kirez", "start": 75, "end": 85,
         "text": "Tamam yarin halledecegim. Ayrica haftaya pazartesiye kadar kullanici analiz raporunu hazirlayabilirim."},
        {"speaker": "Merve Catalkaya", "start": 85, "end": 95,
         "text": "Cok iyi. Ben de cuma gunune kadar on-boarding akisini yeniden tasarlayacagim. Bu yuksek oncelikli."},
        {"speaker": "Ilgin Kirez", "start": 95, "end": 105,
         "text": "Tamamdir. Eger A/B test sonuclari olumlu gelirse dashboard tasarimini da guncelleriz."},
    ]

    llm = GroqLLM()
    print(f"\n  Model: {llm.model}")
    print(f"  Meeting date: {meeting_date}")
    print(f"  Beklenen tarihler:")
    print(f"    yarin       -> 2026-04-26")
    print(f"    haftaya pzt -> 2026-04-27 veya 2026-05-04")
    print(f"    cuma        -> 2026-05-01 veya 2026-04-25")

    print(f"\n--- LLM'e gonderiliyor... ---")
    t0 = time.perf_counter()
    result = llm.complete_json(
        system_prompt=ACTION_ITEM_SYSTEM_PROMPT,
        user_prompt=json.dumps(
            {"meeting_date": meeting_date, "segments": segments, "transcript": transcript},
            ensure_ascii=False, indent=2,
        ),
        temperature=0.1,
    )
    elapsed = time.perf_counter() - t0
    print(f"  LLM yanit suresi: {elapsed:.2f}s")

    # Normalize
    utils_path = PROJECT_ROOT / "src" / "services" / "ai_agents" / "utils.py"
    spec = importlib.util.spec_from_file_location("ai_agents_utils", str(utils_path))
    utils_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(utils_mod)

    print(f"\n{'=' * 70}")
    print(f"  SONUCLAR")
    print(f"{'=' * 70}")

    items_with_date = 0
    raw_items = result.get("action_items", [])

    for i, item in enumerate(raw_items, 1):
        task = item.get("task", "?")
        assignee = item.get("assignee", "")
        raw_date = str(item.get("due_date", "")).strip()
        normalized_date = utils_mod.normalize_due_date(raw_date)
        priority = item.get("priority", "")
        item_type = item.get("type", "")
        confidence = item.get("confidence", 0)

        if raw_date:
            items_with_date += 1

        print(f"\n  [{i}] {task}")
        print(f"      Atanan:          {assignee or '(belirsiz)'}")
        print(f"      Ham tarih:       {raw_date or '(yok)'}")
        print(f"      Normalize tarih: {normalized_date or '(gecersiz/yok)'}")
        print(f"      Oncelik:         {priority or '(belirsiz)'}")
        print(f"      Tip:             {item_type}")
        print(f"      Guven:           {confidence}")

    print(f"\n{'=' * 70}")
    print(f"  DEGERLENDIRME")
    print(f"{'=' * 70}")
    print(f"  Toplam aksiyon:          {len(raw_items)}")
    print(f"  Tarih iceren:            {items_with_date}")

    if items_with_date > 0:
        print(f"\n  [BASARILI] Goreli tarih cevirme CALISIYOR!")
    else:
        print(f"\n  [BASARISIZ] LLM tarih ceviremedi.")

    # Sonucu kaydet
    output_path = PROJECT_ROOT / "tests" / "relative_date_test_result.json"
    output_path.write_text(
        json.dumps({"meeting_date": meeting_date, "raw_response": result}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\n  Detayli sonuc: {output_path.name}")
    print(f"  {'=' * 70}")


if __name__ == "__main__":
    run_test()
