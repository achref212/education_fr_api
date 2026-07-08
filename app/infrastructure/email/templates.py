import base64
from urllib.parse import quote


def _encode_copy_value(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii").rstrip("=")


def _build_copy_page_url(dashboard_url: str, value: str) -> str:
    base = dashboard_url.rstrip("/")
    encoded = quote(_encode_copy_value(value), safe="")
    return f"{base}/copy#v={encoded}"


def _build_copy_button_html(dashboard_url: str, value: str, label: str = "Copier") -> str:
    copy_url = _build_copy_page_url(dashboard_url, value)
    return f"""<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:16px;">
                <tr>
                  <td align="center">
                    <a href="{copy_url}"
                       style="display:inline-block;background:#ffffff;color:#1a73e8;
                              text-decoration:none;font-size:13px;font-weight:700;
                              padding:10px 22px;border-radius:8px;
                              border:2px solid #bee3f8;">
                      📋&nbsp;{label}
                    </a>
                  </td>
                </tr>
              </table>"""


def _build_plain_copy_row(value: str, label: str) -> str:
    return f"""<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:12px;">
                <tr>
                  <td style="background-color:#ffffff;border:1px dashed #cbd5e0;
                             border-radius:8px;padding:12px 14px;">
                    <p style="margin:0 0 6px;color:#718096;font-size:11px;
                               font-weight:600;letter-spacing:1px;text-transform:uppercase;">
                      {label}
                    </p>
                    <p style="margin:0;color:#1a365d;font-size:15px;font-weight:700;
                               font-family:'Courier New',Courier,monospace;
                               -webkit-user-select:all;user-select:all;-moz-user-select:all;">
                      {value}
                    </p>
                  </td>
                </tr>
              </table>"""


def build_school_welcome_email_html(
    school_name: str,
    email: str,
    plain_password: str,
    dashboard_url: str,
) -> str:
    """Build a welcome email for a newly created school account."""
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Bienvenue sur DELFy — Accès établissement</title>
</head>
<body style="margin:0;padding:0;background-color:#f0f4f8;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background-color:#f0f4f8;padding:40px 16px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" border="0"
               style="max-width:600px;width:100%;background-color:#ffffff;
                      border-radius:16px;overflow:hidden;
                      box-shadow:0 4px 24px rgba(0,0,0,0.08);">
          <tr>
            <td align="center"
                style="background:linear-gradient(135deg,#1a73e8 0%,#0d47a1 100%);
                       padding:40px 32px 32px;">
              <img src="cid:logo" alt="DELFy"
                   width="90" height="90"
                   style="display:block;margin:0 auto 20px;border-radius:18px;
                          box-shadow:0 4px 16px rgba(0,0,0,0.25);" />
              <h1 style="margin:0;color:#ffffff;font-size:26px;font-weight:700;">DELFy</h1>
              <p style="margin:8px 0 0;color:rgba(255,255,255,0.85);font-size:14px;">
                Plateforme d&apos;apprentissage du français
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:40px 40px 32px;">
              <h2 style="margin:0 0 16px;color:#1a202c;font-size:22px;font-weight:700;">
                Bienvenue sur DELFy&nbsp;!
              </h2>
              <p style="margin:0 0 12px;color:#4a5568;font-size:15px;line-height:1.7;">
                L&apos;établissement <strong style="color:#1a202c;">{school_name}</strong>
                a été enregistré sur la plateforme DELFy.
              </p>
              <p style="margin:0 0 28px;color:#4a5568;font-size:15px;line-height:1.7;">
                Voici vos identifiants de connexion au tableau de bord :
              </p>
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="margin-bottom:28px;">
                <tr>
                  <td style="background:linear-gradient(135deg,#ebf4ff 0%,#e8edf7 100%);
                             border:2px solid #bee3f8;border-radius:12px;padding:24px 20px;">
                    <table width="100%" cellpadding="0" cellspacing="0" border="0">
                      <tr>
                        <td style="padding-bottom:12px;">
                          <p style="margin:0 0 4px;color:#2b6cb0;font-size:12px;
                                     font-weight:600;letter-spacing:1px;text-transform:uppercase;">
                            Adresse e-mail
                          </p>
                          <p style="margin:0;color:#1a365d;font-size:16px;font-weight:700;
                                     font-family:'Courier New',Courier,monospace;">
                            {email}
                          </p>
                          {_build_copy_button_html(dashboard_url, email, "Copier l'e-mail")}
                        </td>
                      </tr>
                      <tr>
                        <td>
                          <p style="margin:0 0 4px;color:#2b6cb0;font-size:12px;
                                     font-weight:600;letter-spacing:1px;text-transform:uppercase;">
                            Mot de passe
                          </p>
                          <p style="margin:0;color:#1a365d;font-size:16px;font-weight:700;
                                     font-family:'Courier New',Courier,monospace;">
                            {plain_password}
                          </p>
                          {_build_copy_button_html(dashboard_url, plain_password, "Copier le mot de passe")}
                          {_build_plain_copy_row(plain_password, "Copie rapide — mot de passe")}
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="margin-bottom:28px;">
                <tr>
                  <td align="center">
                    <a href="{dashboard_url}"
                       style="display:inline-block;background:linear-gradient(135deg,#1a73e8,#0d47a1);
                              color:#ffffff;text-decoration:none;font-size:15px;font-weight:700;
                              padding:14px 32px;border-radius:8px;">
                      Accéder au tableau de bord
                    </a>
                  </td>
                </tr>
              </table>
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td style="background-color:#fffbeb;border-left:4px solid #f6ad55;
                             border-radius:0 8px 8px 0;padding:14px 16px;">
                    <p style="margin:0;color:#744210;font-size:13px;line-height:1.6;">
                      🔒&nbsp;<strong>Conseil sécurité :</strong>
                      Veuillez changer votre mot de passe dès votre première connexion.
                      Ne partagez jamais ces identifiants.
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding:0 40px;">
              <hr style="border:none;border-top:1px solid #e2e8f0;margin:0;" />
            </td>
          </tr>
          <tr>
            <td style="padding:24px 40px 32px;">
              <p style="margin:0;color:#a0aec0;font-size:12px;text-align:center;">
                &copy; 2026 DELFy &mdash; Tous droits réservés
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def build_prof_welcome_email_html(
    prof_name: str,
    email: str,
    plain_password: str,
    dashboard_url: str,
) -> str:
    """Build a welcome email for a newly created professor account."""
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Bienvenue sur DELFy — Accès professeur</title>
</head>
<body style="margin:0;padding:0;background-color:#f0f4f8;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background-color:#f0f4f8;padding:40px 16px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" border="0"
               style="max-width:600px;width:100%;background-color:#ffffff;
                      border-radius:16px;overflow:hidden;
                      box-shadow:0 4px 24px rgba(0,0,0,0.08);">
          <tr>
            <td align="center"
                style="background:linear-gradient(135deg,#1a73e8 0%,#0d47a1 100%);
                       padding:40px 32px 32px;">
              <img src="cid:logo" alt="DELFy"
                   width="90" height="90"
                   style="display:block;margin:0 auto 20px;border-radius:18px;
                          box-shadow:0 4px 16px rgba(0,0,0,0.25);" />
              <h1 style="margin:0;color:#ffffff;font-size:26px;font-weight:700;">DELFy</h1>
              <p style="margin:8px 0 0;color:rgba(255,255,255,0.85);font-size:14px;">
                Plateforme d&apos;apprentissage du français
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:40px 40px 32px;">
              <h2 style="margin:0 0 16px;color:#1a202c;font-size:22px;font-weight:700;">
                Bienvenue sur DELFy, {prof_name}&nbsp;!
              </h2>
              <p style="margin:0 0 28px;color:#4a5568;font-size:15px;line-height:1.7;">
                Un compte professeur a été créé pour vous sur la plateforme DELFy.
                Voici vos identifiants d&apos;accès :
              </p>
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="margin-bottom:28px;">
                <tr>
                  <td style="background:linear-gradient(135deg,#ebf4ff 0%,#e8edf7 100%);
                             border:2px solid #bee3f8;border-radius:12px;padding:24px 20px;">
                    <table width="100%" cellpadding="0" cellspacing="0" border="0">
                      <tr>
                        <td style="padding-bottom:12px;">
                          <p style="margin:0 0 4px;color:#2b6cb0;font-size:12px;
                                     font-weight:600;letter-spacing:1px;text-transform:uppercase;">
                            Adresse e-mail
                          </p>
                          <p style="margin:0;color:#1a365d;font-size:16px;font-weight:700;
                                     font-family:'Courier New',Courier,monospace;">
                            {email}
                          </p>
                          {_build_copy_button_html(dashboard_url, email, "Copier l'e-mail")}
                        </td>
                      </tr>
                      <tr>
                        <td>
                          <p style="margin:0 0 4px;color:#2b6cb0;font-size:12px;
                                     font-weight:600;letter-spacing:1px;text-transform:uppercase;">
                            Mot de passe
                          </p>
                          <p style="margin:0;color:#1a365d;font-size:16px;font-weight:700;
                                     font-family:'Courier New',Courier,monospace;">
                            {plain_password}
                          </p>
                          {_build_copy_button_html(dashboard_url, plain_password, "Copier le mot de passe")}
                          {_build_plain_copy_row(plain_password, "Copie rapide — mot de passe")}
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="margin-bottom:28px;">
                <tr>
                  <td align="center">
                    <a href="{dashboard_url}"
                       style="display:inline-block;background:linear-gradient(135deg,#1a73e8,#0d47a1);
                              color:#ffffff;text-decoration:none;font-size:15px;font-weight:700;
                              padding:14px 32px;border-radius:8px;">
                      Accéder à mon espace
                    </a>
                  </td>
                </tr>
              </table>
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td style="background-color:#fffbeb;border-left:4px solid #f6ad55;
                             border-radius:0 8px 8px 0;padding:14px 16px;">
                    <p style="margin:0;color:#744210;font-size:13px;line-height:1.6;">
                      🔒&nbsp;<strong>Conseil sécurité :</strong>
                      Veuillez changer votre mot de passe dès votre première connexion.
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding:0 40px;">
              <hr style="border:none;border-top:1px solid #e2e8f0;margin:0;" />
            </td>
          </tr>
          <tr>
            <td style="padding:24px 40px 32px;">
              <p style="margin:0;color:#a0aec0;font-size:12px;text-align:center;">
                &copy; 2026 DELFy &mdash; Tous droits réservés
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def build_activation_code_email_html(
    first_name: str,
    code: str,
    expires_minutes: int,
    dashboard_url: str,
) -> str:
    """Build a beautiful, inline-CSS HTML email for account activation."""
    spaced_code = "&nbsp;".join(list(code))
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Activation de votre compte — DELFy</title>
</head>
<body style="margin:0;padding:0;background-color:#f0f4f8;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background-color:#f0f4f8;padding:40px 16px;">
    <tr>
      <td align="center">

        <!-- Card -->
        <table width="600" cellpadding="0" cellspacing="0" border="0"
               style="max-width:600px;width:100%;background-color:#ffffff;
                      border-radius:16px;overflow:hidden;
                      box-shadow:0 4px 24px rgba(0,0,0,0.08);">

          <!-- Header gradient band -->
          <tr>
            <td align="center"
                style="background:linear-gradient(135deg,#1a73e8 0%,#0d47a1 100%);
                       padding:40px 32px 32px;">
              <!-- Logo -->
              <img src="cid:logo" alt="DELFy"
                   width="90" height="90"
                   style="display:block;margin:0 auto 20px;border-radius:18px;
                          box-shadow:0 4px 16px rgba(0,0,0,0.25);" />
              <h1 style="margin:0;color:#ffffff;font-size:26px;font-weight:700;
                         letter-spacing:-0.3px;">
                DELFy
              </h1>
              <p style="margin:8px 0 0;color:rgba(255,255,255,0.85);font-size:14px;">
                Plateforme d&apos;apprentissage du français
              </p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:40px 40px 32px;">

              <h2 style="margin:0 0 16px;color:#1a202c;font-size:22px;font-weight:700;">
                Bienvenue sur DELFy !
              </h2>

              <p style="margin:0 0 12px;color:#4a5568;font-size:15px;line-height:1.7;">
                Bonjour <strong style="color:#1a202c;">{first_name}</strong>,
              </p>
              <p style="margin:0 0 28px;color:#4a5568;font-size:15px;line-height:1.7;">
                Merci de vous être inscrit. Pour activer votre compte et commencer à apprendre,
                veuillez utiliser le code de vérification ci-dessous.
              </p>

              <!-- Code box -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="margin-bottom:28px;">
                <tr>
                  <td align="center"
                      style="background:linear-gradient(135deg,#ebf4ff 0%,#e8edf7 100%);
                             border:2px solid #bee3f8;border-radius:12px;
                             padding:28px 20px;">
                    <p style="margin:0 0 8px;color:#2b6cb0;font-size:12px;
                               font-weight:600;letter-spacing:2px;text-transform:uppercase;">
                      Votre code d&apos;activation
                    </p>
                    <p style="margin:0;color:#1a365d;font-size:42px;font-weight:800;
                               letter-spacing:12px;font-family:'Courier New',Courier,monospace;">
                      {spaced_code}
                    </p>
                    {_build_copy_button_html(dashboard_url, code, "Copier le code")}
                    {_build_plain_copy_row(code, "Copie rapide — code d'activation")}
                  </td>
                </tr>
              </table>

              <!-- Expiry notice -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="margin-bottom:28px;">
                <tr>
                  <td style="background-color:#fffbeb;border-left:4px solid #f6ad55;
                             border-radius:0 8px 8px 0;padding:14px 16px;">
                    <p style="margin:0;color:#744210;font-size:13px;line-height:1.6;">
                      ⏱&nbsp;<strong>Ce code expire dans {expires_minutes}&nbsp;minutes.</strong>
                    </p>
                  </td>
                </tr>
              </table>

            </td>
          </tr>

          <!-- Divider -->
          <tr>
            <td style="padding:0 40px;">
              <hr style="border:none;border-top:1px solid #e2e8f0;margin:0;" />
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:24px 40px 32px;">
              <p style="margin:0 0 4px;color:#a0aec0;font-size:12px;text-align:center;">
                Vous recevez cet e-mail suite à votre inscription sur DELFy.
              </p>
              <p style="margin:0;color:#a0aec0;font-size:12px;text-align:center;">
                &copy; 2026 DELFy &mdash; Tous droits réservés
              </p>
            </td>
          </tr>

        </table>
        <!-- /Card -->

      </td>
    </tr>
  </table>
</body>
</html>"""


def build_reset_code_email_html(
    first_name: str,
    code: str,
    expires_minutes: int,
    dashboard_url: str,
) -> str:
    """Build a beautiful, inline-CSS HTML email for password reset.

    The logo is referenced as `cid:logo` and attached inline by the SMTP sender.
    """
    spaced_code = "&nbsp;".join(list(code))
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Réinitialisation du mot de passe — DELFy</title>
</head>
<body style="margin:0;padding:0;background-color:#f0f4f8;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background-color:#f0f4f8;padding:40px 16px;">
    <tr>
      <td align="center">

        <!-- Card -->
        <table width="600" cellpadding="0" cellspacing="0" border="0"
               style="max-width:600px;width:100%;background-color:#ffffff;
                      border-radius:16px;overflow:hidden;
                      box-shadow:0 4px 24px rgba(0,0,0,0.08);">

          <!-- Header gradient band -->
          <tr>
            <td align="center"
                style="background:linear-gradient(135deg,#1a73e8 0%,#0d47a1 100%);
                       padding:40px 32px 32px;">
              <!-- Logo -->
              <img src="cid:logo" alt="DELFy"
                   width="90" height="90"
                   style="display:block;margin:0 auto 20px;border-radius:18px;
                          box-shadow:0 4px 16px rgba(0,0,0,0.25);" />
              <h1 style="margin:0;color:#ffffff;font-size:26px;font-weight:700;
                         letter-spacing:-0.3px;">
                DELFy
              </h1>
              <p style="margin:8px 0 0;color:rgba(255,255,255,0.85);font-size:14px;">
                Plateforme d&apos;apprentissage du français
              </p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:40px 40px 32px;">

              <h2 style="margin:0 0 16px;color:#1a202c;font-size:22px;font-weight:700;">
                Réinitialisation du mot de passe
              </h2>

              <p style="margin:0 0 12px;color:#4a5568;font-size:15px;line-height:1.7;">
                Bonjour <strong style="color:#1a202c;">{first_name}</strong>,
              </p>
              <p style="margin:0 0 28px;color:#4a5568;font-size:15px;line-height:1.7;">
                Nous avons reçu une demande de réinitialisation de votre mot de passe.
                Utilisez le code ci-dessous pour créer un nouveau mot de passe.
              </p>

              <!-- Code box -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="margin-bottom:28px;">
                <tr>
                  <td align="center"
                      style="background:linear-gradient(135deg,#ebf4ff 0%,#e8edf7 100%);
                             border:2px solid #bee3f8;border-radius:12px;
                             padding:28px 20px;">
                    <p style="margin:0 0 8px;color:#2b6cb0;font-size:12px;
                               font-weight:600;letter-spacing:2px;text-transform:uppercase;">
                      Votre code de vérification
                    </p>
                    <p style="margin:0;color:#1a365d;font-size:42px;font-weight:800;
                               letter-spacing:12px;font-family:'Courier New',Courier,monospace;">
                      {spaced_code}
                    </p>
                    {_build_copy_button_html(dashboard_url, code, "Copier le code")}
                    {_build_plain_copy_row(code, "Copie rapide — code de vérification")}
                  </td>
                </tr>
              </table>

              <!-- Expiry notice -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="margin-bottom:28px;">
                <tr>
                  <td style="background-color:#fffbeb;border-left:4px solid #f6ad55;
                             border-radius:0 8px 8px 0;padding:14px 16px;">
                    <p style="margin:0;color:#744210;font-size:13px;line-height:1.6;">
                      ⏱&nbsp;<strong>Ce code expire dans {expires_minutes}&nbsp;minutes.</strong>
                      Si vous n&apos;avez pas demandé cette réinitialisation, ignorez
                      simplement cet e-mail.
                    </p>
                  </td>
                </tr>
              </table>

              <!-- Security tip -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td style="background-color:#f7fafc;border:1px solid #e2e8f0;
                             border-radius:8px;padding:14px 16px;">
                    <p style="margin:0;color:#718096;font-size:12px;line-height:1.6;">
                      🔒&nbsp;<strong style="color:#4a5568;">Conseil sécurité :</strong>
                      Ne partagez jamais ce code avec qui que ce soit.
                      L&apos;équipe DELFy ne vous demandera jamais ce code.
                    </p>
                  </td>
                </tr>
              </table>

            </td>
          </tr>

          <!-- Divider -->
          <tr>
            <td style="padding:0 40px;">
              <hr style="border:none;border-top:1px solid #e2e8f0;margin:0;" />
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:24px 40px 32px;">
              <p style="margin:0 0 4px;color:#a0aec0;font-size:12px;text-align:center;">
                Vous recevez cet e-mail car une demande de réinitialisation a été
                effectuée pour votre compte.
              </p>
              <p style="margin:0;color:#a0aec0;font-size:12px;text-align:center;">
                    &copy; 2026 DELFy &mdash; Tous droits réservés
              </p>
            </td>
          </tr>

        </table>
        <!-- /Card -->

      </td>
    </tr>
  </table>
</body>
</html>"""
