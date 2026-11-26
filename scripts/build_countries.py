"""Gera data/reference/countries.json a partir do Natural Earth (domínio público).

Executado uma única vez na montagem do projeto; o arquivo resultante é versionado.
Uso:  python scripts/build_countries.py
"""
from __future__ import annotations

import json
from pathlib import Path

import requests

SOURCE = (
    "https://cdn.jsdelivr.net/gh/nvkelso/natural-earth-vector@v5.1.2/"
    "geojson/ne_50m_admin_0_countries.geojson"
)
OUT = Path(__file__).resolve().parents[1] / "data" / "reference" / "countries.json"

CONTINENT_PT = {
    "South America": "América do Sul",
    "North America": "América do Norte",
    "Europe": "Europa",
    "Asia": "Ásia",
    "Africa": "África",
    "Oceania": "Oceania",
    "Antarctica": "Antártida",
    "Seven seas (open ocean)": "Oceania",
}


def main() -> None:
    resp = requests.get(SOURCE, timeout=60, headers={"User-Agent": "AtlasFluminense/1.0"})
    resp.raise_for_status()
    features = resp.json()["features"]
    out: dict[str, dict] = {}
    for f in features:
        p = f["properties"]
        iso2 = p.get("ISO_A2_EH") or p.get("ISO_A2")
        if not iso2 or iso2 == "-99" or iso2 in out:
            continue
        out[iso2] = {
            "iso2": iso2,
            "iso3": p.get("ISO_A3_EH") or p.get("ISO_A3"),
            "name_pt": p.get("NAME_PT") or p.get("NAME"),
            "name_en": p.get("NAME_EN") or p.get("NAME"),
            "continent": CONTINENT_PT.get(p.get("CONTINENT"), p.get("CONTINENT")),
            "lat": round(float(p.get("LABEL_Y")), 4),
            "lon": round(float(p.get("LABEL_X")), 4),
        }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(dict(sorted(out.items())), ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"{len(out)} países gravados em {OUT}")


if __name__ == "__main__":
    main()
