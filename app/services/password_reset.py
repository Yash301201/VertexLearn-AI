import os
import smtplib
from email.message import EmailMessage
from urllib.parse import quote


def send_password_reset_email(email: str, token: str) -> bool:
    host = os.getenv("SMTP_HOST")
    sender = os.getenv("SMTP_FROM")
    if not host or not sender:
        return False

    frontend_url = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173").rstrip("/")
    reset_url = f"{frontend_url}/?reset_token={quote(token)}"
    message = EmailMessage()
    message["Subject"] = "Reset your VertexLearn password"
    message["From"] = sender
    message["To"] = email
    message.set_content(
        "Use the link below to reset your VertexLearn password. "
        "This link expires in 30 minutes and can only be used once.\n\n"
        f"{reset_url}\n"
    )

    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    if os.getenv("SMTP_USE_SSL", "false").lower() == "true":
        with smtplib.SMTP_SSL(host, port, timeout=10) as server:
            if username and password:
                server.login(username, password)
            server.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=10) as server:
            if os.getenv("SMTP_USE_TLS", "true").lower() == "true":
                server.starttls()
            if username and password:
                server.login(username, password)
            server.send_message(message)
    return True