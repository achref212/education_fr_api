#!/usr/bin/env python3
"""Create an admin user (role=admin). Fails if that email already exists.

Usage:
  export DATABASE_URL=...
  export SECRET_KEY=...
  python scripts/create_admin.py --email admin@example.com --password 'secret' \\
    --first-name Admin --last-name User --level 2e
"""
from __future__ import annotations

import argparse
import os
import sys

# project root: education_fr_api/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import get_settings
from app.core.security import hash_password
from app.infrastructure.db.session import SessionLocal
from app.infrastructure.repositories.sql_admin_user_repository import (
    SqlAdminUserRepository,
)
from app.infrastructure.repositories.sql_user_repository import SqlUserRepository


def main() -> int:
    p = argparse.ArgumentParser(description="Create admin user")
    p.add_argument("--email", required=True)
    p.add_argument("--password", required=True)
    p.add_argument("--first-name", default="Admin", dest="first_name")
    p.add_argument("--last-name", default="User", dest="last_name")
    p.add_argument("--level", default="2e")
    args = p.parse_args()
    _ = get_settings()
    session = SessionLocal()
    try:
        ur = SqlUserRepository(session)
        if ur.get_by_email(args.email):
            print("Error: email already registered", file=sys.stderr)
            return 1
        ar = SqlAdminUserRepository(session)
        ar.create_user_with_role(
            email=args.email,
            password_hash=hash_password(args.password),
            first_name=args.first_name,
            last_name=args.last_name,
            level=args.level,
            role="admin",
        )
        session.commit()
        print("Admin user created:", args.email)
        return 0
    except Exception as e:  # noqa: BLE001
        session.rollback()
        print("Error:", e, file=sys.stderr)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
