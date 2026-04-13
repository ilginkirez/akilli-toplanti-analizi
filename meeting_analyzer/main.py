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
    OPENVIDU_URL=http://localhost:4443
    OPENVIDU_SECRET=MY_SECRET
    SSL_VERIFY=false
"""

import argparse
import logging
import sys
import os

from dotenv import load_dotenv
load_dotenv()

# Proje kökünü path'e ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


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
    openvidu_url = os.getenv("OPENVIDU_URL", "")
    if not openvidu_url:
        print("=" * 65)
        print("  UYARI: OPENVIDU_URL env değişkeni bulunamadı.")
        print("  Backend DEMO modunda başlatılıyor.")
        print("  OpenVidu özelliklerini kullanmak için .env dosyasını")
        print("  oluşturun ve OPENVIDU_URL ile OPENVIDU_SECRET ekleyin.")
        print("=" * 65)

    print("=" * 65)
    print(f"  Meeting Analyzer Backend Başlatılıyor")
    print(f"  Adres : http://{args.host}:{args.port}")
    print(f"  Docs  : http://{args.host}:{args.port}/docs")
    print(f"  OpenVidu: {openvidu_url or 'Demo modu (bağlantı yok)'}")
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
