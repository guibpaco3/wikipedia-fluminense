"""Utilidades de texto: normalização para comparação e busca."""
from __future__ import annotations

import re
import unicodedata

STOPWORDS = {"de", "da", "do", "das", "dos", "e", "o", "a", "os", "as", "em", "no", "na", "x", "vs"}


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def norm(s: str | None) -> str:
    """Minúsculas, sem acentos, sem pontuação, espaços simples."""
    if not s:
        return ""
    s = strip_accents(str(s)).lower().replace("\xa0", " ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def clean(s: str | None) -> str | None:
    """Remove espaços estranhos (inclusive NBSP) preservando acentos."""
    if s is None:
        return None
    s = str(s).replace("\xa0", " ").replace("�", "")
    s = re.sub(r"\s+", " ", s).strip()
    return s or None


def search_terms(query: str) -> list[str]:
    return [t for t in norm(query).split() if t not in STOPWORDS]
