"""Estatísticas calculadas SEMPRE a partir das partidas (nunca números digitados)."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class Record:
    matches: int = 0
    with_score: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    first: dict | None = None
    last: dict | None = None
    biggest_win: dict | None = None
    biggest_loss: dict | None = None

    @property
    def goal_diff(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def points_pct(self) -> float | None:
        """Aproveitamento: pontos conquistados / pontos disputados (vitória = 3)."""
        if not self.with_score:
            return None
        return 100 * (3 * self.wins + self.draws) / (3 * self.with_score)


def _row(df: pd.DataFrame, idx) -> dict:
    return df.loc[idx].to_dict()


def summarize(df: pd.DataFrame) -> Record:
    r = Record(matches=len(df))
    if df.empty:
        return r
    scored = df[df["result"].notna()]
    r.with_score = len(scored)
    r.wins = int((scored["result"] == "V").sum())
    r.draws = int((scored["result"] == "E").sum())
    r.losses = int((scored["result"] == "D").sum())
    r.goals_for = int(scored["flu_goals"].sum())
    r.goals_against = int(scored["opp_goals"].sum())
    ordered = df.sort_values(["date", "kickoff"], na_position="first")
    r.first = ordered.iloc[0].to_dict()
    r.last = ordered.iloc[-1].to_dict()
    if not scored.empty:
        margin = scored["flu_goals"] - scored["opp_goals"]
        wins = scored[margin > 0]
        if not wins.empty:
            m = margin[wins.index]
            best = wins.assign(_m=m, _g=wins["flu_goals"]).sort_values(["_m", "_g", "date"],
                                                                        ascending=[False, False, True])
            r.biggest_win = best.iloc[0].drop(["_m", "_g"]).to_dict()
        losses = scored[margin < 0]
        if not losses.empty:
            m = margin[losses.index]
            worst = losses.assign(_m=m, _g=losses["opp_goals"]).sort_values(["_m", "_g", "date"],
                                                                             ascending=[True, False, True])
            r.biggest_loss = worst.iloc[0].drop(["_m", "_g"]).to_dict()
    return r


def by_group(df: pd.DataFrame, col: str, label: str | None = None) -> pd.DataFrame:
    """Retrospecto agrupado (adversário, árbitro, uniforme, competição, temporada...)."""
    cols = ["Jogos", "V", "E", "D", "GP", "GC", "Saldo", "Aproveitamento %"]
    if df.empty:
        return pd.DataFrame(columns=[label or col, *cols])
    d = df.copy()
    d[col] = d[col].fillna("Não informado")
    g = d.groupby(col, dropna=False)
    out = pd.DataFrame({
        "Jogos": g.size(),
        "V": g["result"].apply(lambda s: int((s == "V").sum())),
        "E": g["result"].apply(lambda s: int((s == "E").sum())),
        "D": g["result"].apply(lambda s: int((s == "D").sum())),
        "GP": g["flu_goals"].sum().astype(int),
        "GC": g["opp_goals"].sum().astype(int),
    })
    out["Saldo"] = out["GP"] - out["GC"]
    disputed = out["V"] + out["E"] + out["D"]
    out["Aproveitamento %"] = (100 * (3 * out["V"] + out["E"]) / (3 * disputed.where(disputed > 0))).round(1)
    out = out.reset_index().rename(columns={col: label or col})
    return out.sort_values("Jogos", ascending=False, ignore_index=True)


def score_text(m: dict) -> str:
    """'Fluminense 2 x 1 Boca Juniors' respeitando mando de campo."""
    fg, og = m.get("flu_goals"), m.get("opp_goals")
    fs = "?" if fg is None or pd.isna(fg) else int(fg)
    os_ = "?" if og is None or pd.isna(og) else int(og)
    if m.get("flu_side") == "visitante":
        txt = f"{m['opponent']} {os_} x {fs} Fluminense"
    else:
        txt = f"Fluminense {fs} x {os_} {m['opponent']}"
    fp, op = m.get("flu_penalties"), m.get("opp_penalties")
    if fp is not None and op is not None and not pd.isna(fp) and not pd.isna(op):
        a, b = (int(op), int(fp)) if m.get("flu_side") == "visitante" else (int(fp), int(op))
        txt += f" (pên. {a} x {b})"
    return txt
