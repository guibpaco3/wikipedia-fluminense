"""Cliente HTTP respeitoso, usado por todos os coletores.

- User-Agent próprio e honesto (sem simular navegador).
- Intervalo mínimo entre requisições ao mesmo host.
- Novas tentativas apenas para 429/5xx, respeitando Retry-After.
- HTTP 401/403 interrompem a coleta: bloqueios NUNCA são contornados.
- Cache em disco opcional, para não repetir downloads.
"""
from __future__ import annotations

import hashlib
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core import config

log = config.get_logger("http")


class AccessDenied(RuntimeError):
    """A fonte recusou o acesso automatizado."""


class PoliteClient:
    def __init__(self, delay: float = config.HTTP_DELAY_SECONDS, timeout: float = config.HTTP_TIMEOUT,
                 cache_dir: Path | None = None, session: requests.Session | None = None):
        self.delay = delay
        self.timeout = timeout
        self.cache_dir = cache_dir
        if cache_dir:
            cache_dir.mkdir(parents=True, exist_ok=True)
        self._last: dict[str, float] = {}
        self.session = session or self._session()
        self.requests_made = 0

    @staticmethod
    def _session() -> requests.Session:
        s = requests.Session()
        retry = Retry(total=3, backoff_factor=2, status_forcelist=(429, 500, 502, 503, 504),
                      allowed_methods=frozenset({"GET", "POST"}), respect_retry_after_header=True,
                      raise_on_status=False)
        s.mount("https://", HTTPAdapter(max_retries=retry))
        s.headers["User-Agent"] = config.HTTP_USER_AGENT
        return s

    def _wait(self, url: str) -> None:
        host = urlparse(url).netloc
        elapsed = time.monotonic() - self._last.get(host, 0)
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self._last[host] = time.monotonic()

    def get(self, url: str, params: dict | None = None, headers: dict | None = None,
            use_cache: bool = False) -> requests.Response | bytes:
        cache_file = None
        if use_cache and self.cache_dir:
            key = hashlib.sha1((url + repr(sorted((params or {}).items()))).encode()).hexdigest()
            cache_file = self.cache_dir / key
            if cache_file.exists():
                return cache_file.read_bytes()
        self._wait(url)
        resp = self.session.get(url, params=params, headers=headers, timeout=self.timeout)
        self.requests_made += 1
        if resp.status_code in (401, 403):
            log.warning("Acesso negado (%s) em %s — coleta interrompida", resp.status_code, url)
            raise AccessDenied(f"{urlparse(url).netloc} recusou o acesso (HTTP {resp.status_code}).")
        resp.raise_for_status()
        if cache_file:
            cache_file.write_bytes(resp.content)
            return resp.content
        return resp

    def get_bytes(self, url: str, **kw) -> bytes:
        r = self.get(url, **kw)
        return r if isinstance(r, bytes) else r.content

    def get_json(self, url: str, **kw):
        import json
        return json.loads(self.get_bytes(url, **kw))
