"""Atualiza data/reference/wikipedia/idolos.json — números dos 30 ídolos nos artigos da Wikipédia.

Uma única requisição em lote à API (até 50 títulos por chamada), com User-Agent identificado.
Guarda, por ídolo: título do artigo, revid (versão citada), jogos/gols pelo Fluminense lidos da
caixa de informações, anos, posição e a miniatura oficial do artigo (upload.wikimedia.org).

Uso:  python scripts/fetch_wiki_idols.py [resposta_salva.json]
"""
from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from modules import wiki_lists as w  # noqa: E402

API = "https://pt.wikipedia.org/w/api.php"
UA = "WikipediaFluminenseBot/0.1 (fan encyclopedia; low-volume)"


def fetch(titles: list[str]) -> dict:
    q = urllib.parse.urlencode({
        "action": "query", "format": "json", "formatversion": "2", "redirects": "1",
        "prop": "revisions|pageimages", "rvprop": "ids|content", "rvslots": "main",
        "piprop": "thumbnail", "pithumbsize": "400", "titles": "|".join(titles)})
    req = urllib.request.Request(f"{API}?{q}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def main() -> None:
    w.idols.cache_clear()
    links = [i.link for i in w.idols()]
    data = (json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")) if len(sys.argv) > 1
            else fetch(links))
    q = data["query"]
    redirect = {r["from"]: r["to"] for r in q.get("redirects", [])}
    pages = {p["title"]: p for p in q["pages"]}
    out = {"_fonte": "Wikipédia (pt), caixas de informações dos artigos dos jogadores",
           "_coletado_em": date.today().isoformat()}
    for link in links:
        p = pages.get(redirect.get(link, link))
        if not p or "revisions" not in p:
            continue
        rev = p["revisions"][0]
        stats = w.infobox_flu_stats(rev["slots"]["main"]["content"])
        out[link] = {"title": p["title"], "revid": rev["revid"],
                     "photo": (p.get("thumbnail") or {}).get("source"), **stats}
    dest = w.WIKI_DIR / "idolos.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(out) - 2} ídolos salvos em {dest}")


if __name__ == "__main__":
    main()
