# DELFy API

Backend FastAPI + PostgreSQL pour l’application [DELFy](../education_fr_app/).

## Prérequis

- Python 3.11+
- PostgreSQL 14+ (ou Docker)

## Configuration

1. Copier l’exemple d’environnement :

   ```bash
   cp .env.example .env
   ```

2. Éditer `.env` : définir `DATABASE_URL`, `SECRET_KEY` (chaîne aléatoire longue en production), et optionnellement `CORS_ORIGINS`.

Pour activer l'envoi d'e-mails de réinitialisation, définir aussi `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`. Sans `SMTP_HOST`, le code est simplement affiché dans les logs (mode développement).

Exemple `DATABASE_URL` :

```text
postgresql://user:password@localhost:5432/education_fr
```

## Base de données (Docker optionnel)

```bash
docker compose up -d
```

Puis par exemple :

```text
DATABASE_URL=postgresql://education_fr:education_fr@localhost:5432/education_fr
```

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Migrations Alembic

```bash
export DATABASE_URL=postgresql://...
alembic upgrade head
```

## Lancer le serveur

```bash
export DATABASE_URL=postgresql://...
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Documentation interactive : <http://localhost:8000/docs>
- Santé : `GET /health`

## Endpoints

### Authentification

| Méthode | Chemin | Auth | Description |
|---------|--------|------|-------------|
| GET | `/health` | Non | Santé du service |
| POST | `/auth/register` | Non | Créer un compte inactif (envoie un code d'activation) |
| POST | `/auth/verify-registration` | Non | Vérifier le code d'activation et obtenir le JWT |
| POST | `/auth/resend-activation` | Non | Renvoyer un code d'activation |
| POST | `/auth/login` | Non | Connexion |
| GET | `/auth/me` | Bearer JWT | Profil courant |
| POST | `/auth/forgot-password` | Non | Demande un code de réinitialisation par e-mail |
| POST | `/auth/verify-reset-code` | Non | Vérifie le code (retourne un `reset_token`) |
| POST | `/auth/reset-password` | Non | Applique le nouveau mot de passe |
| GET | `/progress` | Bearer JWT | Progression |
| PUT | `/progress` | Bearer JWT | Mise à jour progression |

### Flux d'inscription et Activation

```
1. POST /auth/register   { "email": "...", "password": "...", ... }
   → Vérifie l'e-mail (syntaxe, DNS, non jetable).
   → Crée le compte inactif et envoie un code d'activation par e-mail.
   → { "message": "...", "registration_state_token": "<jwt>" }

2. POST /auth/verify-registration { "email": "...", "code": "123456", "registration_state_token": "..." }
   → Vérifie le code. Si valide, active le compte.
   → { "access_token": "...", "user": {...} }

3. POST /auth/resend-activation { "email": "..." }
   → Renvoyer un code si le compte existe et n'est pas encore activé.
```

### Flux de réinitialisation du mot de passe

```
1. POST /auth/forgot-password   { "email": "user@example.com" }
   → Envoie un code à 6 chiffres par e-mail (valable 15 min)

2. POST /auth/verify-reset-code { "email": "…", "code": "123456" }
   → { "reset_token": "<jwt>" }  (valable 15 min, usage unique)

3. POST /auth/reset-password    { "reset_token": "…", "new_password": "…" }
   → { "message": "Mot de passe réinitialisé avec succès." }
```

### Validation d'e-mail à l'inscription

L'API vérifie que l'adresse fournie :
- est syntaxiquement valide,
- possède des enregistrements MX/A valides (DNS),
- n'appartient pas à un domaine de messagerie jetable (mailinator, yopmail, etc.)

Ensuite, un e-mail avec un code d'activation est envoyé pour s'assurer que l'utilisateur a bien accès à cette boîte de réception.

En cas d'échec de la validation DNS/jetable → `422 Unprocessable Entity`.

## Tests

```bash
pytest tests/ -v
```

Les tests d’unité (`AuthService`) et le test HTTP `/health` ne nécessitent pas PostgreSQL. Les tests complets d’intégration avec la base se font en démarrant Postgres et en définissant `DATABASE_URL`.

## Architecture

Domaine (`app/domain/`) — entités et ports.  
Application (`app/application/`) — cas d’usage.  
Infrastructure (`app/infrastructure/`) — SQLAlchemy, repositories.  
API (`app/api/`) — schémas Pydantic et routers FastAPI.
