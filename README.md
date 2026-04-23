# Education FR API

Backend FastAPI + PostgreSQL pour l’application [education_fr](../education_fr/).

## Prérequis

- Python 3.11+
- PostgreSQL 14+ (ou Docker)

## Configuration

1. Copier l’exemple d’environnement :

   ```bash
   cp .env.example .env
   ```

2. Éditer `.env` : définir `DATABASE_URL`, `SECRET_KEY` (chaîne aléatoire longue en production), et optionnellement `CORS_ORIGINS`.

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

## Endpoints (MVP)

| Méthode | Chemin | Auth |
|--------|--------|------|
| GET | `/health` | Non |
| POST | `/auth/register` | Non |
| POST | `/auth/login` | Non |
| GET | `/auth/me` | Bearer JWT |
| GET | `/progress` | Bearer JWT |
| PUT | `/progress` | Bearer JWT |

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
