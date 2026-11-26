"""Atualização incremental pela linha de comando.

Uso:
  python scripts/update_data.py                 # Brasileirão + Wikidata (títulos, jogadores, técnicos)
  python scripts/update_data.py --stadiums      # inclui geolocalização dos estádios (lento: ~1 req/s)
  python scripts/update_data.py --csv arquivo.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collectors import brasileirao_dataset, csv_import, wikidata  # noqa: E402
from database.migrations import migrate  # noqa: E402
from modules.search import rebuild_index  # noqa: E402


def show(r: dict) -> None:
    print({k: v for k, v in r.items() if k != "messages"})
    for m in r["messages"][:15]:
        print("  ", m)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stadiums", action="store_true")
    ap.add_argument("--csv")
    ap.add_argument("--skip-auto", action="store_true")
    a = ap.parse_args()
    migrate()
    if not a.skip_auto:
        show(brasileirao_dataset.collect())
        show(wikidata.collect(("titles", "players", "coaches")))
    if a.stadiums:
        show(wikidata.collect(("stadiums",)))
    if a.csv:
        show(csv_import.import_csv(Path(a.csv).read_text(encoding="utf-8-sig"), "cli"))
    print("Índice de busca:", rebuild_index(), "documentos")


if __name__ == "__main__":
    main()
