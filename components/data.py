"""Consultas cacheadas para as páginas. O painel chama `clear()` após qualquer alteração."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from database.connection import query_df
from modules import coverage, globe
from modules.filters import MatchFilter, fetch_matches

TTL = 3600


@st.cache_data(ttl=TTL, show_spinner=False)
def matches(f: MatchFilter | None = None) -> pd.DataFrame:
    return fetch_matches(f)


@st.cache_data(ttl=TTL, show_spinner=False)
def df(sql: str, params: tuple = ()) -> pd.DataFrame:
    return query_df(sql, params)


@st.cache_data(ttl=TTL, show_spinner=False)
def coverage_text() -> str:
    return coverage.coverage_sentence()


@st.cache_data(ttl=TTL, show_spinner=False)
def coverage_summary() -> dict:
    return coverage.summary()


@st.cache_data(ttl=TTL, show_spinner=False)
def globe_points() -> list[dict]:
    return globe.country_points()


@st.cache_data(ttl=TTL, show_spinner=False)
def world_totals() -> dict:
    return globe.world_totals()


def options(sql: str) -> dict:
    """{id: rótulo} para multiselects."""
    d = df(sql)
    return dict(zip(d.iloc[:, 0], d.iloc[:, 1])) if not d.empty else {}


def clear() -> None:
    st.cache_data.clear()
