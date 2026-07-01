import logging

from email_validator import EmailNotValidError, validate_email

logger = logging.getLogger(__name__)

_DISPOSABLE_DOMAINS: frozenset[str] = frozenset(
    {
        "mailinator.com",
        "yopmail.com",
        "yopmail.fr",
        "yopmail.net",
        "guerrillamail.com",
        "guerrillamail.biz",
        "guerrillamail.de",
        "guerrillamail.info",
        "guerrillamail.net",
        "guerrillamail.org",
        "guerrillamailblock.com",
        "grr.la",
        "spam4.me",
        "10minutemail.com",
        "10minutemail.net",
        "tempmail.com",
        "temp-mail.org",
        "temp-mail.io",
        "trashmail.com",
        "trashmail.me",
        "trashmail.net",
        "trashmail.at",
        "trashmail.io",
        "trashmail.xyz",
        "sharklasers.com",
        "getnada.com",
        "maildrop.cc",
        "discard.email",
        "dispostable.com",
        "throwawaymail.com",
        "throwam.com",
        "fakeinbox.com",
        "mailnull.com",
        "mailnesia.com",
        "mailismagic.com",
        "mailzilla.com",
        "mailslapping.com",
        "bccto.me",
        "chacuo.net",
        "emailondeck.com",
        "filzmail.com",
        "getairmail.com",
        "getonemail.com",
        "jetable.fr.nf",
        "megamailbox.com",
        "mintemail.com",
        "moakt.com",
        "moncourrier.fr.nf",
        "monemail.fr.nf",
        "monmail.fr.nf",
        "mytempemail.com",
        "objectmail.com",
        "obobbo.com",
        "odnorazovoe.ru",
        "one-time.email",
        "oneoffmail.com",
        "pecinan.com",
        "poopiehead.com",
        "powered.name",
        "randomail.net",
        "snkmail.com",
        "sofort-mail.de",
        "spamfree24.org",
        "spamgob.com",
        "spamgourmet.com",
        "spamspot.com",
        "tempr.email",
        "trbvm.com",
        "wegwerfemail.de",
        "willhackforfood.biz",
        "willselfdestruct.com",
        "xagloo.com",
        "xemaps.com",
        "xents.com",
        "xmaily.com",
        "xoxy.net",
        "zehnminutenmail.de",
        "zoemail.net",
        "nwldx.com",
    }
)


class InvalidEmailError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def validate_real_email(email: str) -> str:
    """Validate email syntax, DNS deliverability, and reject disposable domains.

    Returns normalized email on success.
    Raises InvalidEmailError with a French message on any failure.
    """
    try:
        info = validate_email(email, check_deliverability=True)
        normalized: str = info.normalized
    except EmailNotValidError as exc:
        raise InvalidEmailError(
            "L'adresse e-mail fournie est invalide ou inexistante."
        ) from exc

    domain = normalized.split("@", 1)[-1].lower()
    if domain in _DISPOSABLE_DOMAINS:
        raise InvalidEmailError(
            "Les adresses e-mail temporaires ou jetables ne sont pas autorisées."
        )

    return normalized
