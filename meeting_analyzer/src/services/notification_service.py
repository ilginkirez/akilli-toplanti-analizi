"""
notification_service.py
-----------------------
Toplanti sonrasi gorev bildirim servisi.
Sadece assigned_to_user_id doldu ve ambiguous=false olan gorevler icin
ilgili kullaniciya email gonderir.
Bir kisiye birden fazla gorev atanmissa tek mail icerisinde listeler.
"""

import logging
from typing import Any, Optional

from .email_service import EmailConfigError, EmailSendError, is_email_configured, send_email

logger = logging.getLogger("meeting_analyzer.notification_service")

EMAIL_SUBJECT = "Yeni toplantı göreviniz var"

PRIORITY_LABELS = {
    "low": "Düşük",
    "medium": "Orta",
    "high": "Yüksek",
    "critical": "Kritik",
    "urgent": "Acil",
}


def notify_assignees(
    action_items: list[dict[str, Any]],
    meeting_participants: list[dict[str, Any]],
    dashboard_url: Optional[str] = None,
) -> list[dict[str, Any]]:
    """
    Gorev atanan kisilere email gonderir.

    Args:
        action_items: LLM'in cikardigi action item listesi.
        meeting_participants: Toplanti katilimcilari [{user_id, name, email}, ...].
        dashboard_url: Dashboard linki (opsiyonel).

    Returns:
        notifications_sent: Gonderilen bildirimlerin listesi.
            [{"user_id": "...", "email": "...", "name": "...", "tasks_count": N}]
    """
    if not action_items:
        logger.info("Bildirim: Gorev listesi bos, mail gonderilmeyecek.")
        return []

    if not is_email_configured():
        logger.warning(
            "Bildirim: SMTP yapilandirmasi eksik, mail gonderimi atlanacak."
        )
        return []

    # user_id → {name, email} haritasi
    user_map: dict[str, dict[str, str]] = {}
    for participant in meeting_participants:
        user_id = participant.get("user_id")
        email = participant.get("email", "").strip()
        name = participant.get("name", "").strip()
        if user_id and email:
            user_map[user_id] = {"name": name or email, "email": email}

    if not user_map:
        logger.info("Bildirim: Email bilgisi olan katilimci bulunamadi.")
        return []

    # user_id → görev listesi gruplama
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in action_items:
        user_id = item.get("assigned_to_user_id")
        ambiguous = item.get("ambiguous", False)

        # Filtreleme kuralları
        if not user_id:
            continue
        if ambiguous:
            logger.debug(
                "Bildirim: Belirsiz gorev atlaniyor: task=%s",
                item.get("task", "")[:60],
            )
            continue
        if user_id not in user_map:
            logger.warning(
                "Bildirim: user_id=%s katilimci listesinde bulunamadi, atlaniyor.",
                user_id,
            )
            continue

        grouped.setdefault(user_id, []).append(item)

    if not grouped:
        logger.info("Bildirim: Mail gonderilecek gorev atamasi bulunamadi.")
        return []

    # Her kullanıcıya tek mail gönder
    notifications_sent: list[dict[str, Any]] = []

    for user_id, tasks in grouped.items():
        user_info = user_map[user_id]
        email = user_info["email"]
        name = user_info["name"]

        try:
            html_body = _build_email_body(
                name=name,
                tasks=tasks,
                dashboard_url=dashboard_url,
            )
            send_email(
                to_email=email,
                subject=EMAIL_SUBJECT,
                html_body=html_body,
                from_name="Akıllı Toplantı Analizi",
            )
            notifications_sent.append({
                "user_id": user_id,
                "email": email,
                "name": name,
                "tasks_count": len(tasks),
            })
            logger.info(
                "Bildirim gonderildi: user_id=%s email=%s gorev_sayisi=%d",
                user_id,
                email,
                len(tasks),
            )
        except (EmailConfigError, EmailSendError) as exc:
            logger.error(
                "Bildirim gonderilemedi: user_id=%s email=%s hata=%s",
                user_id,
                email,
                exc,
            )
        except Exception as exc:
            logger.error(
                "Bildirim beklenmeyen hata: user_id=%s email=%s hata=%s",
                user_id,
                email,
                exc,
            )

    logger.info(
        "Bildirim ozeti: %d/%d kullaniciya basariyla gonderildi.",
        len(notifications_sent),
        len(grouped),
    )
    return notifications_sent


def _build_email_body(
    name: str,
    tasks: list[dict[str, Any]],
    dashboard_url: Optional[str] = None,
) -> str:
    """Gorev bildirimi icin HTML email icerigi olusturur."""
    task_rows = ""
    for task in tasks:
        task_title = task.get("task", "Belirtilmemiş")
        due_date = task.get("due_date", "")
        priority = task.get("priority", "")
        priority_label = PRIORITY_LABELS.get(priority, "")

        due_html = ""
        if due_date:
            due_html = f"""
            <tr>
              <td style="padding:2px 8px;color:#6b7280;font-size:13px;">📅 Teslim:</td>
              <td style="padding:2px 8px;font-size:13px;">{due_date}</td>
            </tr>"""

        priority_html = ""
        if priority_label:
            priority_color = _priority_color(priority)
            priority_html = f"""
            <tr>
              <td style="padding:2px 8px;color:#6b7280;font-size:13px;">⚡ Öncelik:</td>
              <td style="padding:2px 8px;font-size:13px;">
                <span style="background:{priority_color};color:#fff;padding:2px 8px;border-radius:4px;font-size:12px;">
                  {priority_label}
                </span>
              </td>
            </tr>"""

        task_rows += f"""
        <div style="background:#f9fafb;border-left:4px solid #3b82f6;padding:12px 16px;margin-bottom:12px;border-radius:0 8px 8px 0;">
          <div style="font-weight:600;font-size:15px;color:#1f2937;margin-bottom:6px;">
            {task_title}
          </div>
          <table style="border-collapse:collapse;">
            {due_html}
            {priority_html}
          </table>
        </div>"""

    dashboard_section = ""
    if dashboard_url:
        dashboard_section = f"""
        <div style="text-align:center;margin-top:24px;">
          <a href="{dashboard_url}"
             style="display:inline-block;background:#3b82f6;color:#ffffff;
                    text-decoration:none;padding:12px 24px;border-radius:8px;
                    font-weight:600;font-size:14px;">
            Dashboard'da Görüntüle
          </a>
        </div>"""

    return f"""
    <!DOCTYPE html>
    <html lang="tr">
    <head><meta charset="UTF-8"></head>
    <body style="margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f3f4f6;">
      <div style="max-width:600px;margin:24px auto;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.1);">

        <div style="background:linear-gradient(135deg,#3b82f6,#1d4ed8);padding:24px 32px;">
          <h1 style="margin:0;color:#ffffff;font-size:20px;font-weight:600;">
            📋 Yeni Toplantı Görevleriniz
          </h1>
        </div>

        <div style="padding:24px 32px;">
          <p style="color:#374151;font-size:15px;margin-top:0;">
            Merhaba <strong>{name}</strong>,
          </p>
          <p style="color:#6b7280;font-size:14px;">
            Toplantı sonrası size atanan görevler:
          </p>

          {task_rows}

          {dashboard_section}
        </div>

        <div style="background:#f9fafb;padding:16px 32px;text-align:center;border-top:1px solid #e5e7eb;">
          <p style="margin:0;color:#9ca3af;font-size:12px;">
            Bu email Akıllı Toplantı Analizi sistemi tarafından otomatik gönderilmiştir.
          </p>
        </div>
      </div>
    </body>
    </html>
    """


def _priority_color(priority: str) -> str:
    """Oncelik seviyesine gore renk kodu dondurur."""
    colors = {
        "low": "#22c55e",
        "medium": "#f59e0b",
        "high": "#ef4444",
        "critical": "#dc2626",
        "urgent": "#dc2626",
    }
    return colors.get(priority, "#6b7280")
