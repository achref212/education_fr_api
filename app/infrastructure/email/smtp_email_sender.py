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
    build_prof_welcome_email_html,
    build_reset_code_email_html,
    build_school_welcome_email_html,
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

    def send_school_welcome(
        self,
        to_email: str,
        school_name: str,
        plain_password: str,
        dashboard_url: str,
    ) -> None:
        html_body = build_school_welcome_email_html(
            school_name=school_name,
            email=to_email,
            plain_password=plain_password,
            dashboard_url=dashboard_url,
        )
        msg = MIMEMultipart("related")
        msg["Subject"] = f"Accès tableau de bord DELFy — {school_name}"
        msg["From"] = f"{self._from_name} <{self._from_email}>"
        msg["To"] = to_email
        alternative = MIMEMultipart("alternative")
        msg.attach(alternative)
        plain_text = (
            f"Bienvenue sur DELFy !\n\n"
            f"Établissement : {school_name}\n"
            f"E-mail : {to_email}\n"
            f"Mot de passe : {plain_password}\n\n"
            f"Tableau de bord : {dashboard_url}\n\n"
            "Veuillez changer votre mot de passe dès la première connexion.\n\n"
            "— DELFy"
        )
        alternative.attach(MIMEText(plain_text, "plain", "utf-8"))
        alternative.attach(MIMEText(html_body, "html", "utf-8"))
        if _LOGO_PATH.exists():
            with _LOGO_PATH.open("rb") as logo_file:
                logo_part = MIMEImage(logo_file.read())
            logo_part.add_header("Content-ID", "<logo>")
            logo_part.add_header("Content-Disposition", "inline", filename="logo.png")
            msg.attach(logo_part)
        self._dispatch(msg.as_string(), to_email)
        logger.info("School welcome email sent to %s", to_email)

    def send_prof_welcome(
        self,
        to_email: str,
        prof_name: str,
        plain_password: str,
        dashboard_url: str,
    ) -> None:
        html_body = build_prof_welcome_email_html(
            prof_name=prof_name,
            email=to_email,
            plain_password=plain_password,
            dashboard_url=dashboard_url,
        )
        msg = MIMEMultipart("related")
        msg["Subject"] = "Accès professeur DELFy — Vos identifiants"
        msg["From"] = f"{self._from_name} <{self._from_email}>"
        msg["To"] = f"{prof_name} <{to_email}>"
        alternative = MIMEMultipart("alternative")
        msg.attach(alternative)
        plain_text = (
            f"Bonjour {prof_name},\n\n"
            f"Un compte professeur DELFy a été créé pour vous.\n"
            f"E-mail : {to_email}\n"
            f"Mot de passe : {plain_password}\n\n"
            f"Espace professeur : {dashboard_url}\n\n"
            "Veuillez changer votre mot de passe dès la première connexion.\n\n"
            "— DELFy"
        )
        alternative.attach(MIMEText(plain_text, "plain", "utf-8"))
        alternative.attach(MIMEText(html_body, "html", "utf-8"))
        if _LOGO_PATH.exists():
            with _LOGO_PATH.open("rb") as logo_file:
                logo_part = MIMEImage(logo_file.read())
            logo_part.add_header("Content-ID", "<logo>")
            logo_part.add_header("Content-Disposition", "inline", filename="logo.png")
            msg.attach(logo_part)
        self._dispatch(msg.as_string(), to_email)
        logger.info("Prof welcome email sent to %s", to_email)

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

    def send_school_welcome(
        self,
        to_email: str,
        school_name: str,
        plain_password: str,
        dashboard_url: str,
    ) -> None:
        logger.warning(
            "[DEV] School welcome for %s (%s): password=%s  dashboard=%s",
            to_email,
            school_name,
            plain_password,
            dashboard_url,
        )

    def send_prof_welcome(
        self,
        to_email: str,
        prof_name: str,
        plain_password: str,
        dashboard_url: str,
    ) -> None:
        logger.warning(
            "[DEV] Prof welcome for %s (%s): password=%s  dashboard=%s",
            to_email,
            prof_name,
            plain_password,
            dashboard_url,
        )
