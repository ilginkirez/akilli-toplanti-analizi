"""
email_service.py
----------------
SMTP tabanli email gonderme servisi.
Gmail SMTP ile uyumlu.

.env ayarlari:
    SMTP_HOST=smtp.gmail.com
    SMTP_PORT=587
    SMTP_USER=your-email@gmail.com
    SMTP_PASSWORD=your-app-password
    FROM_EMAIL=your-email@gmail.com
"""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger("meeting_analyzer.email_service")


class EmailConfigError(Exception):
    """SMTP yapilandirmasi eksik."""


class EmailSendError(Exception):
    """Mail gonderimi sirasinda hata."""


def _get_smtp_config() -> dict[str, str | int]:
    """SMTP yapilandirmasini .env'den okur."""
    host = os.getenv("SMTP_HOST", "").strip()
    port_str = os.getenv("SMTP_PORT", "587").strip()
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    from_email = os.getenv("FROM_EMAIL", "").strip()

    if not all([host, user, password, from_email]):
        raise EmailConfigError(
            "SMTP yapilandirmasi eksik. "
            "SMTP_HOST, SMTP_USER, SMTP_PASSWORD ve FROM_EMAIL "
            ".env dosyasinda tanimlanmali."
        )

    try:
        port = int(port_str)
    except ValueError:
        port = 587

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "from_email": from_email,
    }


def is_email_configured() -> bool:
    """SMTP yapilandirmasinin mevcut olup olmadigini kontrol eder."""
    try:
        _get_smtp_config()
        return True
    except EmailConfigError:
        return False


def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    from_name: Optional[str] = None,
) -> None:
    """
    Tek bir aliciya HTML formatta email gonderir.

    Args:
        to_email: Alici email adresi.
        subject: Mail konusu.
        html_body: HTML formatta mail icerigi.
        from_name: Gonderici adi (opsiyonel).

    Raises:
        EmailConfigError: SMTP yapilandirmasi eksikse.
        EmailSendError: Mail gonderimi basarisizsa.
    """
    config = _get_smtp_config()

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["To"] = to_email

    if from_name:
        msg["From"] = f"{from_name} <{config['from_email']}>"
    else:
        msg["From"] = str(config["from_email"])

    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(str(config["host"]), int(config["port"])) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(str(config["user"]), str(config["password"]))
            server.sendmail(str(config["from_email"]), to_email, msg.as_string())

        logger.info("Email basariyla gonderildi: to=%s subject=%s", to_email, subject)
    except smtplib.SMTPException as exc:
        logger.error("Email gonderimi basarisiz: to=%s hata=%s", to_email, exc)
        raise EmailSendError(f"Email gonderilemedi: {exc}") from exc
    except OSError as exc:
        logger.error("SMTP baglanti hatasi: to=%s hata=%s", to_email, exc)
        raise EmailSendError(f"SMTP baglanti hatasi: {exc}") from exc
