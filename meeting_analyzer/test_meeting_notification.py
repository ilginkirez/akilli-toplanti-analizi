import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# src dizinini yola ekleyelim
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from src.services.notification_service import notify_assignees

def run_test():
    session_path = Path("src/storage/sessions/meet-m-62478a64/session.json")
    if not session_path.exists():
        print("HATA: meet-m-62478a64 (Toplantı 11) session dosyası bulunamadı.")
        return

    # 1. Oturum (Session) Verilerini Oku
    with open(session_path, "r", encoding="utf-8") as f:
        session = json.load(f)
    
    # 2. Görevleri (Action Items) Oku
    ai_analysis = session.get("ai_analysis", {})
    raw_action_items = ai_analysis.get("action_items", [])
    
    print(f"Toplantı 11 için {len(raw_action_items)} adet görev (action item) bulundu.")
    
    # Formatı güncelleyelim (Eski versiyondaysa assignee_id -> assigned_to_user_id)
    action_items = []
    for item in raw_action_items:
        action_items.append({
            "task": item.get("title", item.get("task", "")),
            "assigned_to_user_id": item.get("assignee_id") or item.get("assigned_to_user_id"),
            "ambiguous": item.get("needs_review") or item.get("ambiguous", False),
            "priority": item.get("priority", "medium"),
            "due_date": item.get("due_date"),
        })

    # 3. Katılımcıları Ayarla
    # Veritabanında e-postanız kayıtlı olmadığı için test amaçlı manuel veriyoruz.
    meeting_participants = [
        {
            "user_id": "person-merve-atalkaya",
            "name": "Merve Çatalkaya",
            "email": os.getenv("FROM_EMAIL") # Sizin e-postanıza gidecek
        }
    ]

    print("\nE-posta gönderme işlemi başlatılıyor...")
    sent = notify_assignees(action_items, meeting_participants)
    
    if sent:
        print(f"\n✅ BAŞARILI! Toplam {len(sent)} kişiye e-posta gönderildi.")
        for s in sent:
            print(f" - İsim: {s['name']} | E-posta: {s['email']} | Gönderilen Görev Sayısı: {s['tasks_count']}")
    else:
        print("\n❌ Bildirim gönderilemedi veya uygun görev/katılımcı bulunamadı.")

if __name__ == "__main__":
    run_test()
