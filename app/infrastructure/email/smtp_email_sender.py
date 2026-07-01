import logging
import smtplib
import ssl
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import certifi

from app.domain.ports import IEmailSender
from app.infrastructure.email.templates import (
    build_activation_code_email_html,
    build_reset_code_email_html,
)

logger = logging.getLogger(__name__)

_LOGO_PATH = Path(__file__).resolve().parent.parent.parent / "assets" / "logo.png"


class SmtpEmailSender(IEmailSender):
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        from_email: str,
        from_name: str,
        use_ssl: bool = False,
        use_tls: bool = True,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._from_email = from_email
        self._from_name = from_name
        self._use_ssl = use_ssl
        self._use_tls = use_tls

    def send_password_reset_code(
        self,
        to_email: str,
        to_name: str,
        code: str,
        expires_minutes: int,
    ) -> None:
        html_body = build_reset_code_email_html(to_name, code, expires_minutes)

        msg = MIMEMultipart("related")
        msg["Subject"] = "Votre code de réinitialisation — DELFy"
        msg["From"] = f"{self._from_name} <{self._from_email}>"
        msg["To"] = f"{to_name} <{to_email}>"

        alternative = MIMEMultipart("alternative")
        msg.attach(alternative)

        plain_text = (
            f"Bonjour {to_name},\n\n"
            f"Votre code de réinitialisation est : {code}\n\n"
            f"Ce code expire dans {expires_minutes} minutes.\n\n"
            "Si vous n'avez pas demandé cette réinitialisation, ignorez cet e-mail.\n\n"
            "— DELFy"
        )
        alternative.attach(MIMEText(plain_text, "plain", "utf-8"))
        alternative.attach(MIMEText(html_body, "html", "utf-8"))

        if _LOGO_PATH.exists():
            with _LOGO_PATH.open("rb") as logo_file:
                logo_part = MIMEImage(logo_file.read())
            logo_part.add_header("Content-ID", "<logo>")
            logo_part.add_header(
                "Content-Disposition", "inline", filename="logo.png"
            )
            msg.attach(logo_part)

        self._dispatch(msg.as_string(), to_email)
        logger.info("Password reset code sent to %s", to_email)

    def send_activation_code(
        self,
        to_email: str,
        to_name: str,
        code: str,
        expires_minutes: int,
    ) -> None:
        html_body = build_activation_code_email_html(to_name, code, expires_minutes)

        msg = MIMEMultipart("related")
        msg["Subject"] = "Activation de votre compte — DELFy"
        msg["From"] = f"{self._from_name} <{self._from_email}>"
        msg["To"] = f"{to_name} <{to_email}>"

        alternative = MIMEMultipart("alternative")
        msg.attach(alternative)

        plain_text = (
            f"Bonjour {to_name},\n\n"
            f"Votre code d'activation est : {code}\n\n"
            f"Ce code expire dans {expires_minutes} minutes.\n\n"
            "— DELFy"
        )
        alternative.attach(MIMEText(plain_text, "plain", "utf-8"))
        alternative.attach(MIMEText(html_body, "html", "utf-8"))

        if _LOGO_PATH.exists():
            with _LOGO_PATH.open("rb") as logo_file:
                logo_part = MIMEImage(logo_file.read())
            logo_part.add_header("Content-ID", "<logo>")
            logo_part.add_header(
                "Content-Disposition", "inline", filename="logo.png"
            )
            msg.attach(logo_part)

        self._dispatch(msg.as_string(), to_email)
        logger.info("Activation code sent to %s", to_email)

    def _dispatch(self, raw_message: str, to_email: str) -> None:
        context = ssl.create_default_context(cafile=certifi.where())
        if self._use_ssl:
            # Port 465 — wrap the connection in SSL from the start
            with smtplib.SMTP_SSL(self._host, self._port, context=context) as server:
                if self._username:
                    server.login(self._username, self._password)
                server.sendmail(self._from_email, [to_email], raw_message)
        else:
            # Port 587 (or plain) — upgrade to TLS via STARTTLS if requested
            with smtplib.SMTP(self._host, self._port) as server:
                if self._use_tls:
                    server.starttls(context=context)
                if self._username:
                    server.login(self._username, self._password)
                server.sendmail(self._from_email, [to_email], raw_message)


class ConsoleFallbackEmailSender(IEmailSender):
    """Development fallback: prints the code to the console when SMTP is unconfigured."""

    def send_password_reset_code(
        self,
        to_email: str,
        to_name: str,
        code: str,
        expires_minutes: int,
    ) -> None:
        logger.warning(
            "[DEV] Password reset code for %s (%s): %s  (expires in %d min)",
            to_email,
            to_name,
            code,
            expires_minutes,
        )

    def send_activation_code(
        self,
        to_email: str,
        to_name: str,
        code: str,
        expires_minutes: int,
    ) -> None:
        logger.warning(
            "[DEV] Activation code for %s (%s): %s  (expires in %d min)",
            to_email,
            to_name,
            code,
            expires_minutes,
        )
