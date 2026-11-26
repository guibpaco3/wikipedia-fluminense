"""Autenticação do painel: PBKDF2-SHA256 com sal, comparação em tempo constante e bloqueio
temporário após tentativas falhas. A senha nunca é armazenada em texto."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time

ITERATIONS = 390_000
MAX_ATTEMPTS = 5
LOCK_SECONDS = 300


def hash_password(password: str, iterations: int = ITERATIONS) -> str:
    if len(password) < 10:
        raise ValueError("A senha deve ter pelo menos 10 caracteres.")
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), iterations).hex()
    return f"pbkdf2_sha256${iterations}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt, digest = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        calc = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iters)).hex()
        return hmac.compare_digest(calc, digest)
    except (ValueError, AttributeError):
        return False


class LoginGuard:
    """Controle de tentativas (guardado na sessão do usuário)."""

    def __init__(self, state: dict):
        self.state = state
        state.setdefault("auth_fail", 0)
        state.setdefault("auth_locked_until", 0.0)

    def locked_for(self) -> int:
        return max(0, int(self.state["auth_locked_until"] - time.time()))

    def attempt(self, user: str, password: str, expected_user: str, stored_hash: str) -> bool:
        if self.locked_for():
            return False
        ok = bool(stored_hash) and hmac.compare_digest(user, expected_user) and verify_password(password, stored_hash)
        if ok:
            self.state["auth_fail"] = 0
            return True
        self.state["auth_fail"] += 1
        if self.state["auth_fail"] >= MAX_ATTEMPTS:
            self.state["auth_locked_until"] = time.time() + LOCK_SECONDS
            self.state["auth_fail"] = 0
        return False
