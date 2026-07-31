from email.message import EmailMessage
import os
import smtplib
import ssl
from typing import Iterable

from dotenv import load_dotenv

load_dotenv()


def _smtp_settings():
    sender = os.getenv("SENDER_EMAIL")
    smtp_user = os.getenv("SMTP_USERNAME")
    smtp_pass = os.getenv("SMTP_PASSWORD")

    if not sender:
        print("SENDER_EMAIL is not configured.")
        return None
    if not smtp_user:
        print("SMTP_USERNAME is not configured.")
        return None
    if not smtp_pass:
        print("SMTP_PASSWORD is not configured.")
        return None

    return sender, smtp_user, smtp_pass


def _send_email_message(msg: EmailMessage) -> bool:
    settings = _smtp_settings()
    if not settings:
        return False

    _sender, smtp_user, smtp_pass = settings
    try:
        with smtplib.SMTP("smtp-relay.brevo.com", 587) as server:
            server.ehlo()
            server.starttls(context=ssl.create_default_context())
            server.ehlo()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


def _build_assets_html_table(assets: list[dict]) -> str:
    rows = []
    for asset in assets:
        asset_tag = str(asset.get("asset_tag") or "-")
        name = str(asset.get("name") or "-")
        model = str(asset.get("model") or "-")
        rows.append(
            f"<tr><td>{asset_tag}</td><td>{name}</td><td>{model}</td></tr>"
        )
    rows_markup = "".join(rows) if rows else "<tr><td>-</td><td>-</td><td>-</td></tr>"
    return (
        "<table border='0' cellpadding='0' cellspacing='0' width='100%' "
        "style='border-collapse:collapse;border:1px solid #dbe3ef;border-radius:8px;overflow:hidden;'>"
        "<thead>"
        "<tr style='background:#eef4fb;color:#22324a;'>"
        "<th align='left' style='padding:10px 12px;border-bottom:1px solid #dbe3ef;font-size:13px;'>Asset Tag</th>"
        "<th align='left' style='padding:10px 12px;border-bottom:1px solid #dbe3ef;font-size:13px;'>Name</th>"
        "<th align='left' style='padding:10px 12px;border-bottom:1px solid #dbe3ef;font-size:13px;'>Model</th>"
        "</tr>"
        "</thead>"
        f"<tbody>{rows_markup}</tbody></table>"
    )


def _build_assets_text_table(assets: list[dict]) -> str:
    lines = ["Asset Tag | Name | Model", "----------------------------------------"]
    for asset in assets:
        asset_tag = str(asset.get("asset_tag") or "-")
        name = str(asset.get("name") or "-")
        model = str(asset.get("model") or "-")
        lines.append(f"{asset_tag} | {name} | {model}")
    if len(lines) == 2:
        lines.append("- | - | -")
    return "\n".join(lines)


def _brand_logo_html() -> str:
    logo_url = (os.getenv("EMAIL_LOGO_URL") or "").strip()
    if not logo_url:
        return ""
    return (
        "<div style='text-align:right;margin-bottom:8px;'>"
        f"<img src='{logo_url}' alt='OIMS Logo' style='max-height:56px;max-width:180px;'/>"
        "</div>"
    )


def _email_shell_html(title: str, subtitle: str, content_html: str) -> str:
    logo_html = _brand_logo_html()
    return (
        "<div style='background:#f5f8fc;padding:24px;font-family:Segoe UI,Arial,sans-serif;color:#1f2a3a;'>"
        "<div style='max-width:680px;margin:0 auto;background:#ffffff;border:1px solid #dbe3ef;"
        "border-top:4px solid #1f4f82;border-radius:10px;padding:20px 22px;'>"
        f"{logo_html}"
        f"<h2 style='margin:0 0 8px 0;color:#1f2a3a;font-size:24px;font-weight:700;'>{title}</h2>"
        f"<p style='margin:0 0 18px 0;color:#4a5b75;font-size:14px;'>{subtitle}</p>"
        f"{content_html}"
        "<p style='margin:18px 0 0 0;color:#4a5b75;font-size:13px;'>"
        "Regards,<br/><strong>OIMS Support Team</strong></p>"
        "</div></div>"
    )


def send_assignment_email(
    to_address: str,
    employee_name: str,
    assigned_by: str,
    assigned_date: str,
    assets: list[dict],
) -> bool:
    settings = _smtp_settings()
    if not settings:
        return False
    sender, _smtp_user, _smtp_pass = settings

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to_address
    msg["Subject"] = "Asset Assignment Notification"

    text_table = _build_assets_text_table(assets)
    html_table = _build_assets_html_table(assets)

    text_body = (
        f"Hello {employee_name or 'Employee'},\n\n"
        "The following asset(s) have been assigned to you.\n\n"
        f"Assigned Date: {assigned_date or '-'}\n"
        f"Assigned By: {assigned_by or '-'}\n\n"
        f"{text_table}\n\n"
        "Regards,\nSupport Team"
    )
    msg.set_content(text_body)

    html_content = (
        f"<p style='margin:0 0 14px 0;'>Hello <strong>{employee_name or 'Employee'}</strong>,</p>"
        "<p style='margin:0 0 14px 0;'>Your account has been updated with new asset assignment details.</p>"
        "<div style='margin:0 0 14px 0;font-size:14px;color:#1f2a3a;'>"
        f"<div><strong>Assigned Date:</strong> {assigned_date or '-'}</div>"
        f"<div><strong>Assigned By:</strong> {assigned_by or '-'}</div>"
        "</div>"
        f"{html_table}"
    )
    html_body = _email_shell_html(
        title="Asset Assignment Notice",
        subtitle="Please review the asset information below.",
        content_html=html_content,
    )
    msg.add_alternative(html_body, subtype="html")

    sent = _send_email_message(msg)
    if sent:
        print("Assignment email sent successfully.")
    return sent


def send_return_email_to_receiver(
    to_address: str,
    receiver_name: str,
    return_by_name: str,
    returned_date: str,
    assets: list[dict],
) -> bool:
    if not to_address or not to_address.strip():
        return False

    settings = _smtp_settings()
    if not settings:
        return False
    sender, _smtp_user, _smtp_pass = settings

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to_address.strip()
    msg["Subject"] = "Asset Return Confirmation"

    text_table = _build_assets_text_table(assets)
    html_table = _build_assets_html_table(assets)

    text_body = (
        f"Hello {receiver_name or 'Receiver'},\n\n"
        "The following asset(s) were safely returned.\n\n"
        f"Returned Date: {returned_date or '-'}\n"
        f"Return By: {return_by_name or '-'}\n\n"
        f"{text_table}\n\n"
        "Regards,\nOIMS Support Team"
    )
    msg.set_content(text_body)

    html_content = (
        f"<p style='margin:0 0 14px 0;'>Hello <strong>{receiver_name or 'Receiver'}</strong>,</p>"
        "<p style='margin:0 0 14px 0;'>The following asset(s) were safely returned.</p>"
        "<div style='margin:0 0 14px 0;font-size:14px;color:#1f2a3a;'>"
        f"<div><strong>Returned Date:</strong> {returned_date or '-'}</div>"
        f"<div><strong>Return By:</strong> {return_by_name or '-'}</div>"
        "</div>"
        f"{html_table}"
    )
    html_body = _email_shell_html(
        title="Asset Return Confirmation",
        subtitle="The return action has been completed successfully.",
        content_html=html_content,
    )
    msg.add_alternative(html_body, subtype="html")

    sent = _send_email_message(msg)
    if sent:
        print("Return email (receiver) sent successfully.")
    return sent


def send_return_email_to_returner(
    to_address: str,
    returner_name: str,
    received_by_name: str,
    returned_date: str,
    assets: list[dict],
) -> bool:
    if not to_address or not to_address.strip():
        return False

    settings = _smtp_settings()
    if not settings:
        return False
    sender, _smtp_user, _smtp_pass = settings

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to_address.strip()
    msg["Subject"] = "Asset Return Receipt"

    text_table = _build_assets_text_table(assets)
    html_table = _build_assets_html_table(assets)

    text_body = (
        f"Hello {returner_name or 'Employee'},\n\n"
        "Your returned asset(s) have been received successfully.\n\n"
        f"Returned Date: {returned_date or '-'}\n"
        f"Received By: {received_by_name or '-'}\n\n"
        f"{text_table}\n\n"
        "Regards,\nOIMS Support Team"
    )
    msg.set_content(text_body)

    html_content = (
        f"<p style='margin:0 0 14px 0;'>Hello <strong>{returner_name or 'Employee'}</strong>,</p>"
        "<p style='margin:0 0 14px 0;'>Your returned asset(s) have been received successfully.</p>"
        "<div style='margin:0 0 14px 0;font-size:14px;color:#1f2a3a;'>"
        f"<div><strong>Returned Date:</strong> {returned_date or '-'}</div>"
        f"<div><strong>Received By:</strong> {received_by_name or '-'}</div>"
        "</div>"
        f"{html_table}"
    )
    html_body = _email_shell_html(
        title="Asset Return Receipt",
        subtitle="This confirms your returned asset has been received.",
        content_html=html_content,
    )
    msg.add_alternative(html_body, subtype="html")

    sent = _send_email_message(msg)
    if sent:
        print("Return email (returner) sent successfully.")
    return sent

def send_otp_email(
    to_address: str,
    otp: str,
    username: str = "User",
) -> bool:
    """
    Send a 4-digit OTP email for password reset.

    Returns:
        True if email sent successfully, False otherwise.
    """

    settings = _smtp_settings()
    if not settings:
        return False
    sender, _smtp_user, _smtp_pass = settings

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to_address
    msg["Subject"] = "Password Reset Verification Code"

    body = f"""
Hello {username},

We received a request to reset your password.

Your One-Time Password (OTP) is:

    {otp}

This OTP is valid for 10 minutes.

If you did not request a password reset, you can safely ignore this email.

Regards,
Support Team
"""

    msg.set_content(body)

    otp_cells = "".join(
        [
            (
                "<td style='width:44px;height:52px;border:1px solid #bfd0e8;"
                "border-radius:10px;text-align:center;font-size:28px;font-weight:700;"
                "color:#173964;background:#f7fbff;'>"
                f"{digit}"
                "</td>"
            )
            for digit in list(str(otp).strip())
        ]
    )
    html_content = (
        f"<p style='margin:0 0 14px 0;'>Hello <strong>{username or 'User'}</strong>,</p>"
        "<p style='margin:0 0 14px 0;'>We received a request to reset your password.</p>"
        "<p style='margin:0 0 8px 0;'>Use the verification code below:</p>"
        "<table role='presentation' cellpadding='0' cellspacing='0' style='margin:6px 0 14px 0;'>"
        f"<tr>{otp_cells}</tr>"
        "</table>"
        "<p style='margin:0 0 8px 0;color:#8a3d00;'><strong>This OTP is valid for 10 minutes.</strong></p>"
        "<p style='margin:0;'>If you did not request a password reset, you can safely ignore this email.</p>"
    )
    html_body = _email_shell_html(
        title="Verification Code",
        subtitle="Complete your sign-in by entering the OTP below.",
        content_html=html_content,
    )
    msg.add_alternative(html_body, subtype="html")

    try:
        if not _send_email_message(msg):
            return False
        print("OTP email sent successfully.")
        return True

    except Exception as e:
        print(f"Failed to send email: {e}")
        return False
