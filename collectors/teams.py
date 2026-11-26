"""Nome canônico de clubes vindos de fontes diferentes (RSSSF, openfootball, datasets).

Só grafia: "Flamengo-RJ", "CR Flamengo" e "Flamengo" são o mesmo clube. Quando um nome
colide com outro clube de OUTRO estado já cadastrado (ex.: "Portuguesa" no Carioca ×
Portuguesa de São Paulo), o nome recebe o sufixo do estado ("Portuguesa-RJ").

A identificação do Fluminense é estrita: "Fluminense-BA", "Fluminense de Feira",
"Fluminense-PI" etc. NUNCA são o Fluminense Football Club.
"""
from __future__ import annotations

import re

from core.text import clean, norm

UFS = {"AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR",
       "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"}

# Código FIFA/COI (e as abreviações da RSSSF) -> ISO 3166-1 alfa-2.
FIFA_ISO2 = {
    "ARG": "AR", "BOL": "BO", "BRA": "BR", "CHI": "CL", "CHL": "CL", "COL": "CO", "ECU": "EC", "PAR": "PY",
    "PRY": "PY", "PER": "PE", "URU": "UY", "URY": "UY", "VEN": "VE", "MEX": "MX", "USA": "US", "CAN": "CA",
    "CRC": "CR", "HON": "HN", "SLV": "SV", "GUA": "GT", "PAN": "PA", "JAM": "JM", "HAI": "HT", "TRI": "TT",
    "KSA": "SA", "EGY": "EG", "MAR": "MA", "TUN": "TN", "ALG": "DZ", "RSA": "ZA", "NGA": "NG", "CMR": "CM",
    "COD": "CD", "SEN": "SN", "CIV": "CI", "GHA": "GH", "MLI": "ML", "ESP": "ES", "POR": "PT", "ENG": "GB",
    "SCO": "GB", "WAL": "GB", "NIR": "GB", "GER": "DE", "FRA": "FR", "ITA": "IT", "NED": "NL", "BEL": "BE",
    "AUT": "AT", "SUI": "CH", "CRO": "HR", "SRB": "RS", "TUR": "TR", "GRE": "GR", "RUS": "RU", "UKR": "UA",
    "CZE": "CZ", "POL": "PL", "SWE": "SE", "DEN": "DK", "NOR": "NO", "SCG": "RS", "YUG": "RS", "JPN": "JP",
    "KOR": "KR", "CHN": "CN", "AUS": "AU", "NZL": "NZ", "QAT": "QA", "UAE": "AE", "IRN": "IR", "IRQ": "IQ",
    "UZB": "UZ", "IND": "IN", "THA": "TH", "FIJ": "FJ", "PNG": "PG", "TAH": "PF", "SOL": "SB", "NCL": "NC",
}

# Grafias de fontes -> nome canônico (chave = norm(nome [+ UF])).
ALIASES = {
    # Fluminense
    "fluminense": "Fluminense", "fluminense rj": "Fluminense", "fluminense fc": "Fluminense",
    "fluminense football club": "Fluminense", "fluminense fc rj": "Fluminense",
    "fluminense rio de janeiro": "Fluminense", "fluminense r de janeiro": "Fluminense",
    "fluminense fc rio de janeiro": "Fluminense",
    # Rio de Janeiro
    "flamengo rj": "Flamengo", "cr flamengo": "Flamengo", "flamengo": "Flamengo",
    "botafogo rj": "Botafogo", "botafogo fr": "Botafogo", "botafogo": "Botafogo",
    "vasco": "Vasco da Gama", "vasco rj": "Vasco da Gama", "vasco da gama rj": "Vasco da Gama",
    "cr vasco da gama": "Vasco da Gama", "vasco da gama": "Vasco da Gama",
    "america rj": "América-RJ", "portuguesa rj": "Portuguesa-RJ", "paysandu rj": "Paysandu-RJ",
    "america gb": "América-RJ", "canto do rio": "Canto do Rio", "sao cristovao": "São Cristóvão",
    "america tr": "América (Três Rios)", "america tres rios": "América (Três Rios)",
    "s c americano": "S. C. Americano",
    # Demais estados (grafias usuais da RSSSF e do openfootball)
    "america mg": "América-MG", "america fc mg": "América-MG", "america rn": "América-RN",
    "botafogo pb": "Botafogo-PB", "botafogo sp": "Botafogo-SP", "moto club": "Moto Clube",
    "moto club ma": "Moto Clube", "moto clube ma": "Moto Clube", "river pi": "River-PI", "river": "River-PI",
    "luverdense mt": "Luverdense", "uniao s joao": "União São João", "uniao sao joao sp": "União São João",
    "uniao sao joao": "União São João", "sampaio correa ma": "Sampaio Corrêa", "ypiranga rs": "Ypiranga-RS",
    "operario cg": "Operário-MS", "operario cg mt": "Operário-MS", "botafogo rio de janeiro": "Botafogo", "xv de novembro j": "XV de Novembro (Jaú)", "cene": "CENE", "ceub": "CEUB",
    "inter rs": "Internacional", "inter": "Internacional", "urt mg": "URT", "juventude mt": "Juventude-MT",
    "atletico mg": "Atlético-MG", "atletico mineiro": "Atlético-MG", "ca mineiro": "Atlético-MG",
    "c atletico mineiro": "Atlético-MG", "clube atletico mineiro": "Atlético-MG",
    "atletico pr": "Athletico-PR", "athletico pr": "Athletico-PR", "atletico paranaense": "Athletico-PR",
    "ca paranaense": "Athletico-PR", "athletico paranaense": "Athletico-PR",
    "atletico go": "Atlético-GO", "atletico goianiense": "Atlético-GO", "ac goianiense": "Atlético-GO",
    "internacional rs": "Internacional", "sc internacional": "Internacional",
    "gremio rs": "Grêmio", "gremio fbpa": "Grêmio", "gremio": "Grêmio",
    "sport pe": "Sport", "sport recife": "Sport", "sc recife": "Sport", "sport club recife": "Sport",
    "nautico pe": "Náutico", "nautico": "Náutico", "clube nautico capibaribe": "Náutico",
    "santa cruz pe": "Santa Cruz", "santa cruz fc": "Santa Cruz",
    "palmeiras sp": "Palmeiras", "se palmeiras": "Palmeiras",
    "corinthians sp": "Corinthians", "sc corinthians paulista": "Corinthians", "sc corinthians p": "Corinthians",
    "santos sp": "Santos", "santos fc": "Santos",
    "sao paulo sp": "São Paulo", "sao paulo fc": "São Paulo", "sao paulo": "São Paulo",
    "portuguesa sp": "Portuguesa", "portuguesa de desportos": "Portuguesa", "a portuguesa d": "Portuguesa",
    "guarani sp": "Guarani", "guarani fc": "Guarani", "ponte preta sp": "Ponte Preta",
    "aa ponte preta": "Ponte Preta", "bragantino sp": "Bragantino", "rb bragantino": "Bragantino",
    "red bull bragantino": "Bragantino", "mirassol sp": "Mirassol", "mirassol fc": "Mirassol",
    "sao caetano sp": "São Caetano", "santo andre sp": "Santo André", "barueri sp": "Barueri",
    "cruzeiro mg": "Cruzeiro", "cruzeiro ec": "Cruzeiro", "ipatinga mg": "Ipatinga",
    "bahia ba": "Bahia", "ec bahia": "Bahia", "vitoria ba": "Vitória", "ec vitoria": "Vitória",
    "vitoria": "Vitória",
    "gremio porto alegre": "Grêmio", "chapecoense af": "Chapecoense", "chapecoense": "Chapecoense",
    "sao paulo fc sp": "São Paulo", "cruzeiro belo horizonte": "Cruzeiro",
    "fortaleza ce": "Fortaleza", "fortaleza ec": "Fortaleza", "ceara ce": "Ceará", "ceara sc": "Ceará",
    "ceara": "Ceará",
    "juventude rs": "Juventude", "ec juventude": "Juventude",
    "coritiba pr": "Coritiba", "coritiba fbc": "Coritiba", "coritiba fc": "Coritiba",
    "parana pr": "Paraná", "parana clube": "Paraná", "parana": "Paraná",
    "goias go": "Goiás", "goias ec": "Goiás", "goias": "Goiás",
    "cuiaba mt": "Cuiabá", "cuiaba ec": "Cuiabá", "cuiaba": "Cuiabá",
    "criciuma sc": "Criciúma", "criciuma ec": "Criciúma", "criciuma": "Criciúma",
    "avai sc": "Avaí", "avai fc": "Avaí", "avai": "Avaí",
    "figueirense sc": "Figueirense", "figueirense fc": "Figueirense",
    "chapecoense sc": "Chapecoense", "associacao chapecoense de futebol": "Chapecoense",
    "joinville sc": "Joinville", "joinville ec": "Joinville",
    "paysandu pa": "Paysandu", "paysandu sc": "Paysandu", "remo pa": "Remo", "clube do remo": "Remo",
    "csa al": "CSA", "brasiliense df": "Brasiliense",
}

# Clubes estrangeiros enfrentados pelo Fluminense: grafia da fonte -> (nome de exibição, país ISO2).
# Chave: (norm(nome), país) — o país vem do código da própria fonte ("(ARG)", "Arg");
# chave com país None vale para páginas que não informam o país (RSSSF antigas) e só é usada
# em competições internacionais. Nomes homônimos levam o país no nome de exibição.
FOREIGN: dict[tuple[str, str | None], tuple[str, str]] = {}


def _f(display: str, cc: str, *variants: str, bare: bool = True) -> None:
    for v in (display, *variants):
        FOREIGN[(norm(v), cc)] = (display, cc)
        if bare:
            FOREIGN.setdefault((norm(v), None), (display, cc))


# Argentina
_f("Boca Juniors", "AR", "CA Boca Juniors")
_f("River Plate", "AR", "CA River Plate", bare=False)
_f("Argentinos Juniors", "AR", "AA Argentinos Juniors", "Argentinos Jrs", "Argentinos Jrs.")
_f("Arsenal de Sarandí", "AR", "Arsenal", "Arsenal (Buenos Aires)", "Arsenal de Sarandi")
_f("Ferro Carril Oeste", "AR")
_f("Independiente Rivadavia", "AR", "CS Independiente Rivadavia")
_f("Unión de Santa Fe", "AR", "Union de Santa Fe")
_f("Lanús", "AR", "CA Lanús", "Lanus")
# Bolívia
_f("Bolívar", "BO", "Club Bolívar")
_f("The Strongest", "BO", "Club The Strongest")
_f("San José", "BO", "GV San José", "Club San José")
_f("Nacional Potosí", "BO")
_f("Oriente Petrolero", "BO")
# Chile
_f("Colo-Colo", "CL", "CSD Colo-Colo", "Colo Colo")
_f("Universidad de Chile", "CL", "Club Universidad de Chile")
_f("Huachipato", "CL", "CD Huachipato")
_f("Deportes Antofagasta", "CL", "Antofagasta")
_f("Unión La Calera", "CL", "Union La Calera")
_f("Unión Española", "CL", "Union Española")
# Colômbia
_f("Atlético Nacional", "CO", "Atletico Nacional", "CDC Atlético Nacional")
_f("Junior", "CO", "Atlético Junior", "Junior Barranquilla")
_f("Millonarios", "CO")
_f("Once Caldas", "CO")
_f("Independiente Santa Fe", "CO", "Santa Fe")
# Equador
_f("LDU Quito", "EC", "LDU de Quito", "Liga Deportiva Universitaria", "Liga Deportiva Universitaria de Quito", "LDU")
_f("Barcelona de Guayaquil", "EC", "Barcelona", "Barcelona SC")
_f("Emelec", "EC")
_f("Deportivo Cuenca", "EC")
_f("Universidad Católica (Equador)", "EC", "Universidad Catolica", bare=False)
# Paraguai
_f("Olimpia", "PY", "Club Olimpia", "Olimpia Asuncion", "Olimpia Asunción")
_f("Cerro Porteño", "PY", "Club Cerro Porteño", "Cerro Porteno")
_f("Libertad", "PY", "Libertad (Asunción)", "Club Libertad", "Club Libertad Asuncion")
# Peru
_f("Sporting Cristal", "PE", "CS Cristal")
_f("Alianza Lima", "PE", "Club Alianza Lima")
_f("Alianza Atlético", "PE", "Alianza Atletico")
# Uruguai
_f("Nacional (Uruguai)", "UY", "Nacional", "Club Nacional de Football", bare=False)
_f("Nacional (Uruguai)", "UY", "Nacional (Montevideo)")
_f("Peñarol", "UY", "CA Peñarol", "Penarol")
_f("Defensor Sporting", "UY")
_f("Liverpool (Uruguai)", "UY", "Liverpool", "Liverpool FC", bare=False)
_f("River Plate (Uruguai)", "UY", "River Plate", "River Plate (Montevideo)", bare=False)
# Venezuela
_f("Caracas", "VE", "Caracas FC")
_f("Deportivo La Guaira", "VE", "Deportivo La Guaira FC")
_f("Zamora", "VE", "Zamora FC")
_f("Deportivo Galicia", "VE")
_f("Deportivo Italia", "VE")
# México
_f("América (México)", "MX", "América", "Club América", bare=False)
_f("América (México)", "MX", "América (Mexico City)", "América (Ciudad de México)", "Club América (México)")
# Mundiais
_f("Al Ahly", "EG", "Al Ahly SC")
_f("Manchester City", "GB", "Manchester City FC")
_f("Chelsea", "GB", "Chelsea FC")
_f("Borussia Dortmund", "DE")
_f("Ulsan HD", "KR", "Ulsan HD FC", "Ulsan Hyundai")
_f("Mamelodi Sundowns", "ZA")
_f("Internazionale", "IT", "Inter", "FC Internazionale", "Internazionale Milano")
_f("Al Hilal", "SA", "Al-Hilal")

_FOOTNOTE = re.compile(r"\s*(\[[^\]]*\]|\(\*+\)|\*+|#+)\s*$")
_UF_PAREN = re.compile(r"^(?P<base>.+?)\s*\((?:[^()]*?[-\s])?(?P<uf>[A-Z]{2})\)$")
_UF_DASH = re.compile(r"^(?P<base>.+?)\s*[-/]\s*(?P<uf>[A-Z]{2})$")         # "Vitória-ES", "Botafogo/PB"
_UF_SPACE = re.compile(r"^(?P<base>.+?)\s+(?P<uf>[A-Z]{2})$")
_COUNTRY = re.compile(r"^(?P<base>.+?)\s*\((?P<cc>[A-Z]{3})\)$")


def split_name(raw: str) -> tuple[str, str | None, str | None]:
    """'Atlético(MG)' -> ('Atlético', 'MG', None); 'Boca Juniors (ARG)' -> ('Boca Juniors', None, 'AR')."""
    name = clean(raw) or ""
    prev = None
    while prev != name:
        prev = name
        name = _FOOTNOTE.sub("", name).strip(" .,:;")
    country = None
    m = _COUNTRY.match(name)
    if m and m.group("cc") in FIFA_ISO2:
        name, country = m.group("base").strip(), FIFA_ISO2[m.group("cc")]
        if country != "BR":
            return name, None, country
        # "Fluminense RJ (BRA)": segue para extrair a UF
    for rx in (_UF_PAREN, _UF_DASH, _UF_SPACE):
        m = rx.match(name)
        if m and m.group("uf") in UFS:
            return m.group("base").strip(), m.group("uf"), "BR"
    return name, None, country


def is_fluminense(raw: str, default_state: str | None = None) -> bool:
    base, uf, country = split_name(raw)
    if country not in (None, "BR"):
        return False
    uf = uf or default_state
    if uf not in (None, "RJ"):
        return False
    return ALIASES.get(norm(base)) == "Fluminense"


class TeamNamer:
    """Resolve nomes canônicos consultando os clubes já cadastrados (nome -> estado)."""

    def __init__(self, known: dict[str, str | None]):
        self.known = dict(known)          # nome canônico -> UF (ou None)

    @classmethod
    def from_db(cls, c) -> "TeamNamer":
        return cls({r["name"]: r["state"] for r in c.all("SELECT name, state FROM teams")})

    def canonical(self, raw: str, default_state: str | None = None,
                  country: str | None = None, international: bool = False) -> tuple[str, str | None, str | None]:
        """Retorna (nome, UF, país ISO2).

        `international`: competição internacional — nomes sem país conhecido são procurados
        na tabela de clubes estrangeiros; se não estiverem nela nem forem clubes brasileiros
        conhecidos, o país fica desconhecido (None) em vez de presumido.
        """
        base, uf, cc = split_name(raw)
        country = cc or country
        if is_fluminense(raw, default_state if country in (None, "BR") else None):
            return "Fluminense", "RJ", "BR"
        if international and country != "BR" and uf is None:
            hit = FOREIGN.get((norm(base), country)) or (FOREIGN.get((norm(base), None)) if country is None else None)
            if hit:
                return hit[0], None, hit[1]
        if country not in (None, "BR"):
            return base, None, country
        if international and country is None and uf is None:
            key = norm(base)
            if key not in ALIASES and base not in self.known:
                return base, None, None
        uf_ctx = uf or default_state
        for key in ([norm(f"{base} {uf_ctx}")] if uf_ctx else []) + ([norm(base)] if not uf else []):
            if key in ALIASES:
                name = ALIASES[key]
                self.known.setdefault(name, uf_ctx)
                return name, self.known.get(name) or uf_ctx, "BR"
        if base in self.known:
            known_uf = self.known[base]
            if uf_ctx is None or known_uf in (None, uf_ctx):
                return base, known_uf or uf_ctx, "BR"
            name = f"{base}-{uf_ctx}"
            self.known.setdefault(name, uf_ctx)
            return name, uf_ctx, "BR"
        self.known[base] = uf_ctx
        return base, uf_ctx, "BR" if (uf_ctx or country == "BR") else country
