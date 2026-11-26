"""Configuração central: caminhos, variáveis de ambiente e logs."""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
REFERENCE_DIR = DATA_DIR / "reference"
CACHE_DIR = DATA_DIR / "cache"
LOG_DIR = DATA_DIR / "logs"
IMPORTS_DIR = DATA_DIR / "imports"
MIGRATIONS_DIR = ROOT / "database" / "migrations"


def _load_dotenv() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()

# sqlite:///caminho/relativo.db  ou  postgresql://usuario:senha@host/banco
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DATA_DIR / 'wikipedia.db'}")

ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
# Hash gerado por:  python scripts/set_admin_password.py
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", "")

HTTP_USER_AGENT = os.environ.get(
    "HTTP_USER_AGENT", "WikipediaFluminense/1.0 (enciclopedia educacional; coleta respeitosa)"
)
HTTP_DELAY_SECONDS = float(os.environ.get("HTTP_DELAY_SECONDS", "1.5"))
HTTP_TIMEOUT = float(os.environ.get("HTTP_TIMEOUT", "60"))

FLUMINENSE_NAME = "Fluminense"
FLUMINENSE_WIKIDATA = "Q80987"

for d in (CACHE_DIR, LOG_DIR, IMPORTS_DIR):
    d.mkdir(parents=True, exist_ok=True)

_configured = False


def get_logger(name: str) -> logging.Logger:
    global _configured
    if not _configured:
        root = logging.getLogger("wikiflu")
        root.setLevel(logging.INFO)
        fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
        fh = RotatingFileHandler(LOG_DIR / "app.log", maxBytes=2_000_000, backupCount=3,
                                 encoding="utf-8")
        fh.setFormatter(fmt)
        root.addHandler(fh)
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        sh.setLevel(logging.WARNING)
        root.addHandler(sh)
        _configured = True
    return logging.getLogger(f"wikiflu.{name}")
