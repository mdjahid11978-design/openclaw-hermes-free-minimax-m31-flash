"""Owner-authorized SMTP delivery. Credentials stay in environment variables."""
import os
import smtplib
from email.message import EmailMessage
from email.utils import parseaddr


class EmailConfigurationError(RuntimeError):
    pass


class EmailDeliveryError(RuntimeError):
    pass


class SmtpMailer:
    def __init__(self, environ=None):
        self.env = environ if environ is not None else os.environ

    def send(self, recipient, subject, text_body):
        if not all(isinstance(value, str) for value in (recipient, subject, text_body)):
            raise ValueError("to, subject, and text must be strings")
        host = self.env.get("JAHIDS_SMTP_HOST", "").strip()
        sender = self.env.get("JAHIDS_EMAIL_FROM", "").strip()
        username = self.env.get("JAHIDS_SMTP_USERNAME", "")
        password = self.env.get("JAHIDS_SMTP_PASSWORD", "")
        port = int(self.env.get("JAHIDS_SMTP_PORT", "465"))
        mode = self.env.get("JAHIDS_SMTP_SECURITY", "ssl").lower()
        allowed = {
            item.strip().lower()
            for item in self.env.get("JAHIDS_EMAIL_ALLOWED_RECIPIENTS", "").split(",")
            if item.strip()
        }
        if not host or not sender or not username or not password:
            raise EmailConfigurationError("SMTP host, sender, username, and password must be configured")
        if mode not in {"ssl", "starttls"} or not 1 <= port <= 65535:
            raise EmailConfigurationError("SMTP security must be ssl or starttls and port must be valid")
        parsed_sender = parseaddr(sender)[1]
        parsed_recipient = parseaddr(recipient)[1]
        if parsed_sender != sender or parsed_recipient != recipient or "@" not in recipient:
            raise ValueError("sender and recipient must be valid email addresses")
        if not allowed or recipient.lower() not in allowed:
            raise PermissionError("recipient is not in JAHIDS_EMAIL_ALLOWED_RECIPIENTS")
        if not subject.strip() or len(subject) > 200 or not text_body.strip() or len(text_body) > 10000:
            raise ValueError("subject must be 1-200 characters and message 1-10000 characters")

        message = EmailMessage()
        message["From"] = sender
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(text_body)
        try:
            if mode == "ssl":
                client = smtplib.SMTP_SSL(host, port, timeout=20)
            else:
                client = smtplib.SMTP(host, port, timeout=20)
            with client:
                if mode == "starttls":
                    client.ehlo()
                    client.starttls()
                    client.ehlo()
                client.login(username, password)
                client.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            raise EmailDeliveryError("SMTP delivery failed: " + type(exc).__name__) from exc
        return {"status": "sent", "to": recipient, "from": sender}
