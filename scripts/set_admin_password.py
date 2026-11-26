"""Gera o hash da senha do painel e grava em .env (ADMIN_USER / ADMIN_PASSWORD_HASH).

Uso:  python scripts/set_admin_password.py
"""
from __future__ import annotations

import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.auth import hash_password  # noqa: E402

ENV = Path(__file__).resolve().parents[1] / ".env"


def main() -> None:
    user = input("Usuário do painel [admin]: ").strip() or "admin"
    pw = getpass.getpass("Nova senha (mín. 10 caracteres): ")
    if pw != getpass.getpass("Repita a senha: "):
        sys.exit("As senhas não conferem.")
    h = hash_password(pw)
    lines = [l for l in (ENV.read_text(encoding="utf-8").splitlines() if ENV.exists() else [])
             if not l.startswith(("ADMIN_USER=", "ADMIN_PASSWORD_HASH="))]
    lines += [f"ADMIN_USER={user}", f"ADMIN_PASSWORD_HASH={h}"]
    ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Credenciais gravadas em {ENV}. Reinicie o Streamlit.")


if __name__ == "__main__":
    main()
