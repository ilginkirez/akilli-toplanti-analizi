"""
main.py
-------
Meeting Analyzer Backend Başlatıcı.

Kullanım:
    python main.py                    # Geliştirme modu (reload aktif)
    python main.py --host 0.0.0.0     # Tüm ağ arayüzlerinde dinle
    python main.py --port 8080        # Farklı port
    python main.py --no-reload        # Reload kapalı

.env örnek:
    LIVEKIT_API_URL=http://livekit:7880
    LIVEKIT_WS_URL=wss://rtc.example.com
    LIVEKIT_API_KEY=devkey
    LIVEKIT_API_SECRET=devsecret
"""

import argparse
import logging
import sys
import os

from dotenv import load_dotenv
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Backend'i kendi klasöründen çalıştırarak tüm göreli yolları tek yerde topluyoruz.
os.chdir(BASE_DIR)
load_dotenv(os.path.join(BASE_DIR, ".env"), override=False)
sys.path.insert(0, BASE_DIR)


def main():
    parser = argparse.ArgumentParser(
        description="Meeting Analyzer Backend Sunucusu"
    )
    parser.add_argument("--host",     default="0.0.0.0",  help="Dinlenecek adres (varsayılan: 0.0.0.0)")
    parser.add_argument("--port",     type=int, default=8000, help="Port numarası (varsayılan: 8000)")
    parser.add_argument("--no-reload", action="store_true",   help="Otomatik yeniden yüklemeyi devre dışı bırak")
    parser.add_argument("--log-level", default="info",        help="Log seviyesi (debug/info/warning)")
    args = parser.parse_args()

    try:
        import uvicorn
    except ImportError:
        print("HATA: uvicorn kurulu değil. Kurmak için:")
        print("  pip install uvicorn[standard]")
        sys.exit(1)

    # ENV kontrolü
    livekit_url = os.getenv("LIVEKIT_API_URL", "")
    if not livekit_url:
        print("=" * 65)
        print("  UYARI: LIVEKIT_API_URL env değişkeni bulunamadı.")
        print("  Backend DEMO modunda başlatılıyor.")
        print("  LiveKit özelliklerini kullanmak için .env dosyasını")
        print("  oluşturun ve LIVEKIT_API_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET ekleyin.")
        print("=" * 65)

    print("=" * 65)
    print(f"  Meeting Analyzer Backend Başlatılıyor")
    print(f"  Adres : http://{args.host}:{args.port}")
    print(f"  Docs  : http://{args.host}:{args.port}/docs")
    print(f"  LiveKit: {livekit_url or 'Demo modu (bağlantı yok)'}")
    print("=" * 65)

    uvicorn.run(
        "src.server:app",
        host=args.host,
        port=args.port,
        reload=not args.no_reload,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
