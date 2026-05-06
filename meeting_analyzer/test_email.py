import os
import sys
from dotenv import load_dotenv

# Proje dizinini yola ekleyelim ki src import edilebilsin
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.services.email_service import send_email, is_email_configured

def main():
    # .env dosyasını bir üst dizinden yükle
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    load_dotenv(env_path)

    print("--- Email Gönderme Testi ---")
    
    if not is_email_configured():
        print("HATA: SMTP konfigürasyonu eksik.")
        print("Lütfen projenin kök dizinindeki .env dosyanıza aşağıdaki değişkenleri ekleyin:")
        print("SMTP_HOST=smtp.gmail.com")
        print("SMTP_PORT=587")
        print("SMTP_USER=your-email@gmail.com")
        print("SMTP_PASSWORD=your-app-password")
        print("FROM_EMAIL=your-email@gmail.com")
        return

    print("SMTP konfigürasyonu bulundu.")
    to_email = input("Test emaili kime gönderilsin? (Email adresi girin): ").strip()
    
    if not to_email:
        print("Email adresi girmediniz. Çıkılıyor.")
        return

    subject = "Akıllı Toplantı Analizi - Test Emaili"
    html_body = """
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
                <h2 style="color: #2c3e50;">🚀 Test Başarılı!</h2>
                <p>Merhaba,</p>
                <p>Bu, <b>Akıllı Toplantı Analizi</b> sisteminden gönderilen bir test mailidir.</p>
                <p>Eğer bu maili görüyorsanız, sistemin e-posta entegrasyonu başarılı bir şekilde çalışıyor demektir.</p>
                <br>
                <p style="font-size: 0.9em; color: #7f8c8d;">İyi çalışmalar,<br>Akıllı Toplantı Sistemi</p>
            </div>
        </body>
    </html>
    """

    print(f"\nGönderiliyor: {to_email}...")
    try:
        send_email(
            to_email=to_email,
            subject=subject,
            html_body=html_body,
            from_name="Akıllı Toplantı Sistemi"
        )
        print("✅ Email başarıyla gönderildi!")
    except Exception as e:
        print(f"❌ Email gönderimi sırasında hata oluştu: {e}")

if __name__ == "__main__":
    main()
