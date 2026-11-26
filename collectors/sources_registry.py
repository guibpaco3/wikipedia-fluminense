"""Catálogo das fontes investigadas, com situação de acesso e política de uso.

Registrado no banco para que a página "Fontes e cobertura" mostre de forma
transparente de onde vêm (e de onde NÃO vêm) os dados.
"""
from __future__ import annotations

from database.connection import Conn
from database.repository import ensure_source, manual_source_id

SOURCES = [
    dict(code="brasileirao_dataset", name="Brasileirão Dataset (Adão Duque, GitHub)", kind="dataset",
         base_url="https://github.com/adaoduque/Brasileirao_Dataset",
         license="Não declarada no repositório — uso com crédito", reliability="media", automated=True,
         notes="Série A 2003–atual: partidas, técnicos, estádio, gols (autor/minuto) e cartões. "
               "Coleta automática."),
    dict(code="wikidata", name="Wikidata", kind="api", base_url="https://www.wikidata.org",
         license="CC0 1.0", reliability="media", automated=True,
         notes="Títulos (P1346), jogadores (P54), técnicos (P286), estádios (P625/P131). "
               "Dados colaborativos: entram como 'não verificado'."),
    dict(code="natural_earth", name="Natural Earth", kind="dataset", base_url="https://www.naturalearthdata.com",
         license="Domínio público", reliability="alta", automated=True,
         notes="Países, continentes e coordenadas usados no globo."),
    dict(code="sofascore", name="SofaScore", kind="site", base_url="https://www.sofascore.com",
         license="Termos de uso restritivos", reliability="media", automated=False,
         notes="API recusou acesso automatizado (HTTP 403) em 24/11/2026. Não é contornado. "
               "Uso apenas como referência consultada manualmente."),
    dict(code="transfermarkt", name="Transfermarkt", kind="site", base_url="https://www.transfermarkt.com.br",
         license="Termos proíbem extração automatizada", reliability="media", automated=False,
         notes="Transcrição manual com citação, via painel ou CSV padronizado."),
    dict(code="worldfootball", name="WorldFootball.net", kind="site", base_url="https://www.worldfootball.net",
         license="Termos restritivos", reliability="media", automated=False,
         notes="Recusou acesso automatizado (HTTP 403) em 24/11/2026."),
    dict(code="ogol", name="oGol", kind="site", base_url="https://www.ogol.com.br",
         license="Termos restritivos", reliability="media", automated=False,
         notes="Transcrição manual com citação."),
    dict(code="rsssf", name="RSSSF / RSSSF Brasil", kind="site", base_url="https://www.rsssf.org",
         license="Uso não comercial com crédito", reliability="media", automated=False,
         notes="Melhor fonte para o período pré-2003; páginas em texto livre — transcrição via CSV."),
    dict(code="fluminense_oficial", name="Site oficial do Fluminense", kind="site",
         base_url="https://www.fluminense.com.br", license="Conteúdo editorial do clube",
         reliability="alta", automated=False, notes="Referência para história e institucional."),
    dict(code="csv_import", name="Importação CSV padronizada", kind="manual", reliability="media",
         notes="Arquivos preparados por administradores; cada linha informa sua própria fonte e URL."),
]


def register_sources(c: Conn) -> None:
    manual_source_id(c)
    for s in SOURCES:
        ensure_source(c, s["code"], s["name"], s["kind"], s.get("base_url"), s.get("license"),
                      s.get("reliability", "media"), s.get("automated", False), s.get("notes"))
