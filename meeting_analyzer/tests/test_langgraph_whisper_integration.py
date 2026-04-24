"""
test_langgraph_whisper_integration.py
-------------------------------------
meet-m-eb2b7632 oturumu uzerinde gercek LangGraph + Whisper Large
pipeline'ini uctan uca test eder.

Gereksinimler:
  - GROQ_API_KEY env degiskeni tanimli olmali
  - FFmpeg yolda (PATH) olmali
  - downloaded bundle: downloads/meeting_pull_20260424_oracle/bundles/deneme__meet-m-eb2b7632

Calistirma:
  cd meeting_analyzer
  python -m pytest tests/test_langgraph_whisper_integration.py -v -s
"""

import json
import os
import shutil
import sys
import time
from pathlib import Path

# --- Proje kokunu path'e ekle ------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# --- Bundle yollari -----------------------------------------------------------
BUNDLE_ROOT = (
    PROJECT_ROOT.parent
    / "downloads"
    / "meeting_pull_20260424_oracle"
    / "bundles"
    / "deneme__meet-m-eb2b7632"
)
SESSION_ID = "meet-m-eb2b7632"
RECORDINGS_DIR = BUNDLE_ROOT / "recordings"
SESSION_STORAGE_DIR = BUNDLE_ROOT / "session_storage"
SESSION_JSON = SESSION_STORAGE_DIR / SESSION_ID / "session.json"

# Bireysel ses dosyalari
AUDIO_ILGIN = RECORDINGS_DIR / SESSION_ID / "individual" / "par_937b69-TR_AMimQVSQwduvXD.ogg"
AUDIO_MERVE = RECORDINGS_DIR / SESSION_ID / "individual" / "par_697f47-TR_AMc3PtQBxjtBMj.ogg"


def _skip_if_missing():
    """Bundle dosyalari veya API key eksikse testi atla."""
    reasons = []
    if not SESSION_JSON.exists():
        reasons.append(f"session.json bulunamadi: {SESSION_JSON}")
    if not AUDIO_ILGIN.exists():
        reasons.append(f"Ilgin ses dosyasi bulunamadi: {AUDIO_ILGIN}")
    if not AUDIO_MERVE.exists():
        reasons.append(f"Merve ses dosyasi bulunamadi: {AUDIO_MERVE}")
    if not os.getenv("GROQ_API_KEY"):
        reasons.append("GROQ_API_KEY tanimli degil")
    return reasons


def _load_session() -> dict:
    return json.loads(SESSION_JSON.read_text(encoding="utf-8"))


def _print_banner(title: str):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


# ==============================================================================
# TEST 1: Ses dosyalarinin varligini ve formatini dogrula
# ==============================================================================
def test_01_audio_files_exist_and_valid():
    """Bundle'daki bireysel ses dosyalarinin varligini kontrol et."""
    _print_banner("TEST 1: Ses Dosyalari Kontrolu")

    problems = _skip_if_missing()
    if problems:
        for p in problems:
            print(f"  [!] {p}")
        import pytest
        pytest.skip("Gerekli dosya/key eksik: " + "; ".join(problems))

    for label, path in [("Ilgin", AUDIO_ILGIN), ("Merve", AUDIO_MERVE)]:
        assert path.exists(), f"{label} ses dosyasi bulunamadi: {path}"
        size_kb = path.stat().st_size / 1024
        assert size_kb > 10, f"{label} ses dosyasi cok kucuk: {size_kb:.1f} KB"
        print(f"  [OK] {label}: {path.name} ({size_kb:.0f} KB)")

    print("  [OK] Tum ses dosyalari mevcut ve gecerli boyutta")


# ==============================================================================
# TEST 2: Session JSON yapisini dogrula
# ==============================================================================
def test_02_session_structure():
    """Session JSON'daki katilimci ve kayit bilgilerini dogrula."""
    _print_banner("TEST 2: Session Yapisi Kontrolu")

    problems = _skip_if_missing()
    if problems:
        import pytest
        pytest.skip("Gerekli dosya/key eksik")

    session = _load_session()

    assert session["session_id"] == SESSION_ID
    assert len(session["participants"]) == 2

    participant_ids = {p["participant_id"] for p in session["participants"]}
    assert "par_937b69" in participant_ids, "Ilgin Kirez katilimci olarak bulunamadi"
    assert "par_697f47" in participant_ids, "Merve Catalkaya katilimci olarak bulunamadi"

    for p in session["participants"]:
        files = p.get("recording_files", [])
        assert len(files) > 0, f"{p['display_name']} icin kayit dosyasi yok"
        assert files[0]["has_audio"] is True

    recording = session.get("recording", {})
    assert recording.get("has_audio") is True
    assert recording.get("mode") == "LIVEKIT_TRACK_EGRESS"

    print(f"  [OK] Session ID: {SESSION_ID}")
    print(f"  [OK] Katilimcilar: {', '.join(p['display_name'] for p in session['participants'])}")
    print(f"  [OK] Kayit modu: {recording['mode']}")
    print(f"  [OK] Speech segment sayisi: {len(session.get('speech_analysis', {}).get('segments', []))}")


# ==============================================================================
# TEST 3: Whisper Large ile tek dosya transkripsiyon
# ==============================================================================
def test_03_whisper_large_single_file_transcription():
    """Whisper Large ile tek bir ses dosyasinin transkripsiyonunu test et."""
    _print_banner("TEST 3: Whisper Large - Tekli Dosya Transkripsiyon")

    problems = _skip_if_missing()
    if problems:
        import pytest
        pytest.skip("Gerekli dosya/key eksik")

    os.environ.setdefault("AI_TRANSCRIBE_MODEL", "whisper-large-v3")
    from src.services.ai_transcription import transcribe_audio_segments

    print(f"  --> Ilgin Kirez ses dosyasi transkript ediliyor...")
    print(f"      Model: whisper-large-v3")
    print(f"      Dosya: {AUDIO_ILGIN.name}")

    t0 = time.perf_counter()
    segments = transcribe_audio_segments(
        str(AUDIO_ILGIN),
        language="tr",
        speaker="Ilgin Kirez",
        participant_id="par_937b69",
        offset_sec=0.0,
    )
    elapsed = time.perf_counter() - t0

    print(f"  <-- Tamamlandi: {elapsed:.2f}s, {len(segments)} segment\n")

    assert len(segments) > 0, "Hic segment dondurilmedi!"

    for i, seg in enumerate(segments, 1):
        assert "text" in seg and seg["text"].strip(), f"Segment {i} bos metin"
        assert "start" in seg and "end" in seg, f"Segment {i} zaman damgasi eksik"
        assert seg["speaker"] == "Ilgin Kirez"
        assert seg["participant_id"] == "par_937b69"
        print(f"    [{seg['start']:.2f}s - {seg['end']:.2f}s] {seg['text']}")

    total_text = " ".join(s["text"] for s in segments)
    print(f"\n  Toplam karakter: {len(total_text)}")
    print(f"  Toplam segment: {len(segments)}")
    assert len(total_text) > 20, "Toplam metin cok kisa"


# ==============================================================================
# TEST 4: Whisper Large ile segment bazli klip transkripsiyon
# ==============================================================================
def test_04_whisper_large_clip_transcription():
    """Speech analysis segmentlerine gore klip bazli transkripsiyon testi."""
    _print_banner("TEST 4: Whisper Large - Klip Bazli Transkripsiyon")

    problems = _skip_if_missing()
    if problems:
        import pytest
        pytest.skip("Gerekli dosya/key eksik")

    os.environ.setdefault("AI_TRANSCRIBE_MODEL", "whisper-large-v3")
    from src.services.ai_transcription import transcribe_audio_clip_text

    session = _load_session()
    speech_segments = session.get("speech_analysis", {}).get("segments", [])

    # Ilgin'in ilk birkac single segmentini test et
    ilgin_segments = [
        s for s in speech_segments
        if s.get("type") == "single"
        and s.get("participant_id") == "par_937b69"
        and s.get("duration_sec", 0) > 0.5
    ][:3]

    assert len(ilgin_segments) > 0, "Ilgin icin test edilecek segment bulunamadi"

    print(f"  Test edilecek segment sayisi: {len(ilgin_segments)}")

    all_texts = []
    for seg in ilgin_segments:
        start = seg["start_sec"]
        end = seg["end_sec"]
        print(f"\n  --> Segment {seg['segment_id']}: [{start:.2f}s - {end:.2f}s]")

        t0 = time.perf_counter()
        text = transcribe_audio_clip_text(
            str(AUDIO_ILGIN),
            start_sec=start,
            end_sec=end,
            language="tr",
            pad_start_sec=0.35,
            pad_end_sec=0.35,
        )
        elapsed = time.perf_counter() - t0

        print(f"      <-- Metin ({elapsed:.2f}s): {text!r}")
        if text:
            all_texts.append(text)

    assert len(all_texts) > 0, "Hicbir klip segmentinden metin cikarilamadi"
    print(f"\n  [OK] {len(all_texts)}/{len(ilgin_segments)} segmentten metin cikarildi")


# ==============================================================================
# TEST 5: Tam LangGraph pipeline (transcription -> summary -> action items)
# ==============================================================================
def test_05_full_langgraph_pipeline():
    """
    Gercek ses kayitlari uzerinde tam LangGraph pipeline'ini calistir:
      transcription_agent -> summary_agent -> action_item_agent -> finalize
    """
    _print_banner("TEST 5: Tam LangGraph Pipeline")

    problems = _skip_if_missing()
    if problems:
        import pytest
        pytest.skip("Gerekli dosya/key eksik")

    os.environ.setdefault("AI_TRANSCRIBE_MODEL", "whisper-large-v3")

    from src.services.session_store import SessionStore
    from src.services.meeting_store import MeetingStore
    import src.services.ai_analysis_service as ai_module

    # Gecici store olustur (bundle'a yazmamak icin)
    tmp_path = PROJECT_ROOT / "_test_tmp_langgraph"
    tmp_path.mkdir(parents=True, exist_ok=True)
    storage_root = tmp_path / "storage"
    recordings_dir = RECORDINGS_DIR

    store = SessionStore(str(storage_root), str(recordings_dir))
    meetings = MeetingStore(str(tmp_path / "meetings.db"))

    original_session_store = ai_module.session_store
    original_meeting_store = ai_module.meeting_store
    ai_module.session_store = store
    ai_module.meeting_store = meetings

    try:
        session = _load_session()
        store.ensure_session(SESSION_ID)
        store.save_session(SESSION_ID, session)

        service = ai_module.AIAnalysisService(
            recordings_dir=str(recordings_dir),
        )

        print(f"  --> Pipeline baslatiliyor...")
        print(f"      Session: {SESSION_ID}")
        print(f"      Katilimcilar: Ilgin Kirez, Merve Catalkaya")
        print(f"      Whisper model: whisper-large-v3")
        print(f"      LLM model: {service._model_name()}")

        t0 = time.perf_counter()

        # 1) Kaynaklari topla
        sources = service._collect_sources(session)
        t_sources = time.perf_counter() - t0
        print(f"\n  [1/4] Kaynaklar toplandi ({t_sources:.2f}s): {len(sources)} kaynak")
        for src in sources:
            print(f"         - {src.display_name}: {src.relative_path}")

        assert len(sources) == 2, f"2 kaynak beklendi, {len(sources)} bulundu"

        # 2) LangGraph pipeline'i calistir
        print(f"\n  [2/4] LangGraph pipeline calistiriliyor...")
        t1 = time.perf_counter()

        graph_state = service._run_analysis_graph(
            session_id=SESSION_ID,
            session=session,
            sources=sources,
            meeting_date="2026-04-24",
        )
        t_pipeline = time.perf_counter() - t1

        # 3) Sonuclari dogrula
        print(f"\n  [3/4] Pipeline tamamlandi ({t_pipeline:.2f}s)")

        # Transcript segments
        transcript_segments = graph_state.get("transcript_segments", [])
        full_text = graph_state.get("full_text", "")
        print(f"\n  -- Transkript --")
        print(f"     Segment sayisi: {len(transcript_segments)}")
        print(f"     Toplam karakter: {len(full_text)}")
        assert len(transcript_segments) > 0, "Transkript segmenti uretilmedi"
        assert len(full_text) > 50, "Full text cok kisa"

        print(f"\n     Segmentler:")
        for seg in transcript_segments:
            speaker = seg.get("speaker", "?")
            text = seg.get("text", "")
            start = seg.get("start", 0)
            end = seg.get("end", 0)
            truncated = (text[:80] + "...") if len(text) > 80 else text
            print(f"       [{start:.1f}s-{end:.1f}s] {speaker}: {truncated}")

        speakers = {seg.get("speaker") for seg in transcript_segments}
        print(f"\n     Konusmacilar: {speakers}")
        assert len(speakers) >= 1, "En az 1 konusmaci beklendi"

        # Summary
        summary_result = graph_state.get("summary_result", {})
        print(f"\n  -- Ozet --")
        exec_summary = summary_result.get("executiveSummary", "N/A")
        print(f"     Executive Summary: {exec_summary[:150]}")
        print(f"     Kararlar: {summary_result.get('keyDecisions', [])}")
        print(f"     Konular: {summary_result.get('topics', [])}")
        assert summary_result.get("executiveSummary"), "Executive summary bos"

        # Action Items
        action_items = graph_state.get("action_items", [])
        print(f"\n  -- Aksiyon Maddeleri ({len(action_items)}) --")
        for item in action_items:
            print(f"     - [{item.get('priority','?')}] {item.get('task','?')} -> {item.get('assignee','?')}")

        # Summary Output (finalize'd)
        summary_output = graph_state.get("summary_output")
        print(f"\n  -- Finalize Sonucu --")
        if summary_output:
            print(f"     Executive Summary: {summary_output.executiveSummary[:100]}...")
            print(f"     Key Decisions: {summary_output.keyDecisions}")
            print(f"     Topics: {summary_output.topics}")
            print(f"     Action Items: {len(summary_output.actionItems)}")
            for ai_item in summary_output.actionItems:
                print(f"       - {ai_item.title} (assignee: {ai_item.assignee_id})")

        # 4) Genel istatistikler
        total_elapsed = time.perf_counter() - t0
        print(f"\n  [4/4] Genel Istatistikler")
        print(f"     Toplam sure: {total_elapsed:.2f}s")
        print(f"     Kaynak toplama: {t_sources:.2f}s")
        print(f"     Pipeline: {t_pipeline:.2f}s")
        print(f"     Transkript segment: {len(transcript_segments)}")
        print(f"     Aksiyon maddesi: {len(action_items)}")

        # Sonucu dosyaya kaydet
        output_path = BUNDLE_ROOT / "langgraph_test_result.json"
        result_payload = {
            "session_id": SESSION_ID,
            "test_timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "model_whisper": "whisper-large-v3",
            "model_llm": service._model_name(),
            "total_elapsed_sec": round(total_elapsed, 2),
            "transcript_segments": transcript_segments,
            "full_text": full_text,
            "summary_result": summary_result,
            "action_items": action_items,
            "summary_output": summary_output.model_dump(mode="json") if summary_output else None,
        }
        output_path.write_text(
            json.dumps(result_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"\n  Sonuc kaydedildi: {output_path}")
        print(f"\n  [OK] PIPELINE BASARILI!")

    finally:
        ai_module.session_store = original_session_store
        ai_module.meeting_store = original_meeting_store
        # Gecici dosyalari temizle (Windows uyumlu)
        try:
            shutil.rmtree(tmp_path, ignore_errors=True)
        except Exception:
            pass


# ==============================================================================
# TEST 6: Mevcut analiz sonucuyla karsilastirma
# ==============================================================================
def test_06_compare_with_existing_analysis():
    """Yeni pipeline sonuclarini mevcut sunucu analiz sonuclariyla karsilastir."""
    _print_banner("TEST 6: Mevcut Analizle Karsilastirma")

    existing_transcript_path = (
        RECORDINGS_DIR / SESSION_ID / "analysis" / "ai" / "transcript.json"
    )
    result_path = BUNDLE_ROOT / "langgraph_test_result.json"

    if not existing_transcript_path.exists():
        import pytest
        pytest.skip("Mevcut analiz dosyasi bulunamadi")
    if not result_path.exists():
        import pytest
        pytest.skip("test_05 sonuc dosyasi bulunamadi (once test_05'i calistirin)")

    existing = json.loads(existing_transcript_path.read_text(encoding="utf-8"))
    new_result = json.loads(result_path.read_text(encoding="utf-8"))

    existing_segments = existing.get("segments", [])
    new_segments = new_result.get("transcript_segments", [])

    print(f"  Mevcut analiz: {len(existing_segments)} segment")
    print(f"  Yeni analiz:   {len(new_segments)} segment")

    existing_speakers = {s.get("speaker") for s in existing_segments}
    new_speakers = {s.get("speaker") for s in new_segments}

    print(f"\n  Mevcut konusmacilar: {existing_speakers}")
    print(f"  Yeni konusmacilar:   {new_speakers}")

    assert len(new_speakers) >= 1, "Yeni analizde konusmaci bulunamadi"

    existing_text = existing.get("full_text", "")
    new_text = new_result.get("full_text", "")

    print(f"\n  Mevcut metin uzunlugu: {len(existing_text)} karakter")
    print(f"  Yeni metin uzunlugu:   {len(new_text)} karakter")

    assert len(new_text) > 50, "Yeni analiz cok kisa metin uretti"

    new_summary = new_result.get("summary_result", {})

    print(f"\n  -- Yeni Ozet --")
    print(f"     {new_summary.get('executiveSummary', 'N/A')[:200]}")

    print(f"\n  [OK] Karsilastirma tamamlandi")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "-s", "--tb=short"])
