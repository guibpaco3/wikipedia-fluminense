"""Identidade visual: verde #006B3F, grená #7A0019, branco. Layout responsivo."""
from __future__ import annotations

import streamlit as st

GREEN = "#006B3F"
GARNET = "#7A0019"
WHITE = "#FFFFFF"
INK = "#1B1F1D"
MUTED = "#5F6B66"
RESULT_COLORS = {"V": "#0B7A47", "E": "#8A8F8C", "D": "#9B1B30"}
RESULT_LABELS = {"V": "Vitória", "E": "Empate", "D": "Derrota"}

from components.brand import hamburger_uri  # noqa: E402

HAMBURGER_LIGHT = hamburger_uri("#FFFFFF")   # dentro da barra lateral (fundo verde)
HAMBURGER_DARK = hamburger_uri(INK)          # no cabeçalho, com a barra recolhida

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&display=swap');
html, body, [class*="css"], .stMarkdown, .stText {{ font-family: Inter, system-ui, sans-serif; }}
h1, h2, h3 {{ font-family: 'Source Serif 4', Georgia, serif !important; color: {INK}; letter-spacing: -.01em; }}
.block-container {{ padding-top: 3.4rem; max-width: 1320px; }}
[data-testid="stSidebar"] {{ background: linear-gradient(180deg, {GREEN} 0%, #00512F 55%, {GARNET} 140%); }}
[data-testid="stSidebar"] * {{ color: #F3F7F5 !important; }}
[data-testid="stSidebar"] input {{ color: {INK} !important; }}
[data-testid="stSidebarNavLink"][aria-current="page"] {{ background: rgba(255,255,255,.16); }}

.wf-hero {{ position: relative; border-radius: 18px; padding: 30px 34px; color: #fff; overflow: hidden;
  background: linear-gradient(115deg, {GREEN} 0%, {GREEN} 46%, {GARNET} 46.2%, {GARNET} 72%, #FFFFFF 72.2%);
  box-shadow: 0 14px 38px rgba(0,60,35,.18); margin-bottom: 18px; }}
.wf-hero h1 {{ color: #fff !important; font-size: clamp(1.7rem, 3.4vw, 2.7rem); margin: 0 0 6px; }}
.wf-hero p {{ max-width: 60%; font-size: 1.02rem; opacity: .95; margin: 0; }}
.wf-hero .stripe {{ position:absolute; right: 26px; top: 50%; transform: translateY(-50%);
  font: 700 clamp(2.4rem, 6vw, 4.6rem) 'Source Serif 4', serif; color: {GREEN}; opacity: .9; }}

.wf-cov {{ border-left: 4px solid {GARNET}; background: #FBF4F5; padding: 10px 14px; border-radius: 6px;
  color: #4A1520; font-size: .92rem; margin: 6px 0 16px; }}
.wf-note {{ border-left: 4px solid {GREEN}; background: #F1F8F4; padding: 10px 14px; border-radius: 6px;
  color: #0F3B26; font-size: .92rem; margin: 6px 0 14px; }}

.wf-cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin: 8px 0 18px; }}
.wf-card {{ background: #fff; border: 1px solid #E3E8E5; border-radius: 14px; padding: 14px 16px;
  box-shadow: 0 2px 10px rgba(0,0,0,.035); }}
.wf-card .l {{ font-size: .74rem; text-transform: uppercase; letter-spacing: .06em; color: {MUTED}; font-weight: 600; }}
.wf-card .v {{ font: 700 1.75rem 'Source Serif 4', serif; color: {INK}; line-height: 1.15; margin-top: 4px; }}
.wf-card .n {{ font-size: .75rem; color: {MUTED}; margin-top: 2px; }}
.wf-card.g {{ border-top: 4px solid {GREEN}; }} .wf-card.r {{ border-top: 4px solid {GARNET}; }}
.wf-card.n0 {{ border-top: 4px solid #9AA39F; }}

.wf-badge {{ display:inline-block; padding: 2px 9px; border-radius: 999px; font-size: .74rem; font-weight: 600;
  border: 1px solid #D5DBD8; color: {MUTED}; background: #F6F8F7; margin-right: 4px; }}
.wf-badge.ok {{ color: #0B5A35; border-color: #9CCFB4; background: #EAF6EF; }}
.wf-badge.warn {{ color: #7A4A00; border-color: #E9C98F; background: #FFF6E5; }}
.wf-badge.bad {{ color: {GARNET}; border-color: #E2A4B0; background: #FCEEF1; }}

.wf-res {{ display:inline-flex; align-items:center; justify-content:center; width: 26px; height: 26px; border-radius: 7px;
  color:#fff; font-weight:700; font-size:.8rem; }}

.wf-scoreboard {{ display:grid; grid-template-columns: 1fr auto 1fr; align-items:center; gap: 14px;
  background: linear-gradient(90deg, {GREEN}, #00512F 50%, {GARNET}); color:#fff; border-radius: 18px; padding: 24px; }}
.wf-scoreboard .t {{ font: 700 clamp(1.1rem, 2.4vw, 1.7rem) 'Source Serif 4', serif; }}
.wf-scoreboard .t.r {{ text-align: right; }}
.wf-scoreboard .s {{ font: 700 clamp(2rem, 5vw, 3.4rem) 'Source Serif 4', serif; text-align:center; }}
.wf-scoreboard .meta {{ grid-column: 1 / -1; text-align:center; opacity:.9; font-size:.92rem; }}

.wf-cal {{ display:grid; grid-template-columns: repeat(7, 1fr); gap: 5px; }}
.wf-cal .h {{ font-size:.72rem; font-weight:700; color:{MUTED}; text-align:center; text-transform:uppercase; }}
.wf-cal .d {{ min-height: 64px; border-radius: 9px; border: 1px solid #E6EAE8; padding: 4px 6px; font-size: .8rem;
  background:#fff; overflow:hidden; }}
.wf-cal .d.e {{ background: transparent; border: none; }}
.wf-cal .d .n {{ font-weight: 600; color: #8A938F; font-size:.74rem; }}
.wf-cal .d.m {{ border-color: {GREEN}; box-shadow: inset 0 0 0 1px {GREEN}22; }}
.wf-cal .d a {{ display:block; text-decoration:none; color:#fff !important; border-radius:6px; padding:2px 5px; margin-top:3px;
  font-size:.72rem; font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}

.wf-tl {{ border-left: 3px solid {GREEN}; margin-left: 8px; padding-left: 18px; }}
.wf-tl .i {{ position: relative; margin-bottom: 14px; }}
.wf-tl .i::before {{ content:''; position:absolute; left:-26px; top:4px; width:13px; height:13px; border-radius:50%;
  background:{GARNET}; border: 2px solid #fff; box-shadow: 0 0 0 2px {GARNET}; }}
.wf-tl .dt {{ font-weight:700; color:{GREEN}; font-size:.85rem; }}

/* ---------- menu: três linhas no lugar das setas duplas (sempre visível) ---------- */
[data-testid="stSidebarCollapseButton"] {{ display: flex !important; visibility: visible !important; opacity: 1 !important; }}
[data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"],
[data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"] {{
  font-size: 0 !important; color: transparent !important; overflow: hidden; display: inline-block;
  width: 28px; height: 28px; background: url("{HAMBURGER_LIGHT}") center / 28px 28px no-repeat; }}
[data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"] {{ background-image: url("{HAMBURGER_DARK}"); }}
[data-testid="stExpandSidebarButton"] {{ border-radius: 10px; padding: 4px; }}
[data-testid="stExpandSidebarButton"]:hover {{ background: #EEF3F0; }}

/* marca e busca no topo da barra lateral, navegação logo abaixo */
[data-testid="stSidebarContent"] {{ display: flex; flex-direction: column; }}
[data-testid="stSidebarHeader"] {{ order: 0; }}
[data-testid="stSidebarUserContent"] {{ order: 1; padding-top: 0 !important; padding-bottom: .5rem !important; }}
[data-testid="stSidebarNav"] {{ order: 2; }}

/* ---------- marca (símbolo + nome empilhado) ---------- */
.wf-lockup {{ display: flex; align-items: center; gap: 12px; text-decoration: none; }}
.wf-lockup .mark {{ width: 54px; height: 54px; border-radius: 14px; background: #fff; flex: none;
  display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 10px rgba(0,0,0,.12); }}
.wf-lockup .mark img {{ width: 80%; height: 80%; }}
.wf-lockup .name {{ display: flex; flex-direction: column; line-height: .92; }}
.wf-lockup .name b, .wf-lockup .name i {{ font: 700 1.5rem 'Source Serif 4', Georgia, serif; letter-spacing: -.01em; }}
.wf-lockup .name b {{ color: {GARNET}; }} .wf-lockup .name i {{ color: {GREEN}; font-style: normal; }}
.wf-lockup.dark .name b, .wf-lockup.dark .name i {{ color: #fff !important; }}
.wf-lockup.dark .name i {{ opacity: .85; }}
.wf-lockup.lg .mark {{ width: 70px; height: 70px; border-radius: 18px; }}
.wf-lockup.lg .name b, .wf-lockup.lg .name i {{ font-size: 2.05rem; }}
.wf-topbar {{ display: flex; align-items: center; justify-content: space-between; gap: 16px;
  padding: 4px 2px 16px; border-bottom: 1px solid #E3E8E5; margin-bottom: 18px; }}
.wf-topbar .tag {{ color: {MUTED}; font-size: .8rem; font-weight: 600; text-transform: uppercase;
  letter-spacing: .08em; text-align: right; }}
.wf-topbar .tag span {{ display: block; color: {GARNET}; }}

/* ---------- sala de troféus (foto + painel) ---------- */
.wf-room {{ display: grid; grid-template-columns: minmax(0, 5fr) minmax(0, 7fr); border-radius: 22px;
  overflow: hidden; background: #0B1A13; min-height: 580px; box-shadow: 0 20px 50px rgba(0,40,24,.25); }}
.wf-room .photo {{ position: relative; background-size: cover; background-position: center 28%; min-height: 380px; }}
.wf-room .photo .cap {{ position: absolute; left: 0; right: 0; bottom: 0; padding: 40px 18px 12px; color: #fff;
  font-size: .78rem; background: linear-gradient(0deg, rgba(0,0,0,.72), rgba(0,0,0,0)); }}
.wf-room .photo .cap b {{ display: block; font-size: .95rem; }}
.wf-room .panel {{ padding: 34px 40px 28px; color: #fff;
  background: radial-gradient(120% 90% at 100% 0%, #0E5A3A 0%, #08321F 55%, #2A0710 130%); }}
.wf-room .kicker {{ font-size: .76rem; font-weight: 700; letter-spacing: .16em; text-transform: uppercase; opacity: .75; }}
.wf-room h2 {{ color: #fff !important; font-size: clamp(1.6rem, 2.6vw, 2.3rem); margin: 4px 0 24px; }}
.wf-tgrid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 26px 22px; }}
.wf-t .top {{ display: flex; align-items: flex-end; gap: 10px; }}
.wf-t .ic {{ color: #fff; height: 58px; display: flex; align-items: flex-end; }}
.wf-t .ic svg {{ height: 58px; width: auto; }}
.wf-t .num {{ font: 800 3.1rem/0.9 Inter, sans-serif; letter-spacing: -.03em; }}
.wf-t .lbl {{ margin-top: 10px; font-size: .7rem; font-weight: 700; letter-spacing: .04em; hyphens: none; overflow-wrap: normal; word-break: normal; text-transform: uppercase;
  opacity: .92; min-height: 2.3em; }}
.wf-t .bar {{ height: 2px; background: rgba(255,255,255,.18); margin-top: 8px; }}
.wf-t .bar span {{ display: block; height: 100%; background: linear-gradient(90deg, #fff, #9FD8B9); }}
.wf-t .yrs {{ font-size: .7rem; opacity: .6; margin-top: 6px; }}
.wf-room .total {{ margin-top: 26px; padding-top: 16px; border-top: 1px solid rgba(255,255,255,.18);
  display: flex; justify-content: space-between; align-items: baseline; gap: 12px; flex-wrap: wrap; font-size: .82rem; }}
.wf-room .total b {{ font: 800 1.7rem Inter, sans-serif; margin-right: 6px; }}
.wf-room .total a {{ color: #BFE6CF !important; }}
.wf-src {{ color: {MUTED}; font-size: .76rem; margin: 8px 2px 22px; }}
.wf-src a {{ color: {GREEN}; }}

/* ---------- abas no estilo "Decade by decade / Presidents / Coaches" ---------- */
.st-key-home_tabs [role="tablist"] {{ background: #fff; border-bottom: 1px solid #DDE3E0; gap: 0;
  overflow-x: auto; scrollbar-width: none; margin-bottom: 10px; }}
.st-key-home_tabs [data-testid="stTab"] {{ padding: 18px 26px 15px; height: auto; position: relative; }}
.st-key-home_tabs [data-testid="stTab"] p {{ font: 800 .86rem Inter, sans-serif !important; text-transform: uppercase;
  letter-spacing: .06em; color: #8A938F; white-space: nowrap; }}
.st-key-home_tabs [data-testid="stTab"][aria-selected="true"] p {{ color: {INK}; }}
.st-key-home_tabs [data-testid="stTab"]:hover p {{ color: {GARNET}; }}
.st-key-home_tabs .react-aria-SelectionIndicator {{ background: {GARNET} !important; height: 3px !important;
  border-radius: 0 !important; }}
.wf-sec-h {{ display: flex; align-items: baseline; justify-content: space-between; gap: 12px; flex-wrap: wrap;
  margin: 10px 0 6px; }}
.wf-sec-h .t {{ font: 700 1.9rem 'Source Serif 4', Georgia, serif; color: {INK}; }}
.wf-sec-h span {{ color: {MUTED}; font-size: .86rem; }}

/* ---------- Lendas do Clube ---------- */
.wf-legends {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 18px; margin-top: 10px; }}
.wf-leg {{ border-radius: 16px; overflow: hidden; background: #fff; border: 1px solid #E3E8E5;
  box-shadow: 0 6px 18px rgba(0,0,0,.06); display: flex; flex-direction: column; }}
.wf-leg .ph {{ position: relative; height: 240px;
  background: repeating-linear-gradient(90deg, {GARNET} 0 24px, #fff 24px 30px, {GREEN} 30px 54px, #fff 54px 60px); }}
.wf-leg .ph img {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; object-position: center 18%; }}
.wf-leg .ph .ini {{ position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
  font: 700 3.4rem 'Source Serif 4', serif; color: #fff; text-shadow: 0 2px 12px rgba(0,0,0,.45); }}
.wf-leg .ph .rk {{ position: absolute; top: 10px; left: 10px; background: {GARNET}; color: #fff; border-radius: 999px;
  font: 800 .8rem Inter, sans-serif; padding: 4px 10px; box-shadow: 0 2px 6px rgba(0,0,0,.25); }}
.wf-leg .ph::after {{ content: ''; position: absolute; left: 0; right: 0; bottom: 0; height: 8px;
  background: linear-gradient(90deg, {GARNET} 0 33.3%, #fff 33.3% 66.6%, {GREEN} 66.6%); }}
.wf-leg .bd {{ padding: 12px 14px 4px; }}
.wf-leg .nm {{ font: 700 1.2rem 'Source Serif 4', serif; color: {INK}; line-height: 1.15; }}
.wf-leg .meta {{ color: {MUTED}; font-size: .76rem; margin-top: 2px; min-height: 2.2em; }}
.wf-leg .st {{ display: grid; grid-template-columns: 1fr 1fr; margin-top: auto;
  background: linear-gradient(100deg, {GREEN} 0%, #00512F 50%, {GARNET} 100%); color: #fff; }}
.wf-leg .st div {{ padding: 10px 14px; }}
.wf-leg .st div + div {{ border-left: 1px solid rgba(255,255,255,.25); }}
.wf-leg .st b {{ display: block; font: 800 1.6rem/1 Inter, sans-serif; }}
.wf-leg .st small {{ font-size: .66rem; letter-spacing: .08em; text-transform: uppercase; opacity: .85; }}
.wf-leg .st sup {{ font-size: .6rem; opacity: .8; margin-left: 2px; }}

/* ---------- Técnicos / Presidentes / Competições ---------- */
.wf-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(270px, 1fr)); gap: 14px; margin-top: 8px; }}
.wf-item {{ background: #fff; border: 1px solid #E3E8E5; border-radius: 14px; padding: 14px 16px;
  box-shadow: 0 2px 10px rgba(0,0,0,.035); border-top: 4px solid {GREEN}; display: flex; flex-direction: column; gap: 6px; }}
.wf-item.int {{ border-top-color: #A9B3AE; background: #FBFCFB; }}
.wf-item.cur {{ border-top-color: {GARNET}; }}
.wf-item .hd {{ display: flex; justify-content: space-between; gap: 8px; align-items: flex-start; }}
.wf-item .no {{ font: 700 1.9rem/1 'Source Serif 4', serif; color: #C9D2CD; }}
.wf-item .nm {{ font: 700 1.08rem 'Source Serif 4', serif; color: {INK}; line-height: 1.2; }}
.wf-item .pd {{ color: {MUTED}; font-size: .78rem; font-weight: 600; }}
.wf-item .rec {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 4px; text-align: center; margin-top: 4px; }}
.wf-item .rec div {{ background: #F4F7F5; border-radius: 8px; padding: 5px 0; }}
.wf-item .rec b {{ display: block; font: 800 1.05rem Inter, sans-serif; color: {INK}; }}
.wf-item .rec small {{ font-size: .62rem; color: {MUTED}; font-weight: 700; letter-spacing: .06em; }}
.wf-item .rec .v b {{ color: #0B7A47; }} .wf-item .rec .d b {{ color: #9B1B30; }}
.wf-pbar {{ display: flex; height: 6px; border-radius: 99px; overflow: hidden; background: #EEF1EF; }}
.wf-pbar span:nth-child(1) {{ background: #0B7A47; }} .wf-pbar span:nth-child(2) {{ background: #A9B0AD; }}
.wf-pbar span:nth-child(3) {{ background: #9B1B30; }}
.wf-item .ft {{ display: flex; justify-content: space-between; font-size: .75rem; color: {MUTED}; gap: 8px; flex-wrap: wrap; }}
.wf-item .ft b {{ color: {INK}; }}
.wf-item .hl {{ font-size: .74rem; color: #3D4743; border-top: 1px dashed #E3E8E5; padding-top: 6px; }}
.wf-item .none {{ font-size: .78rem; color: {MUTED}; font-style: italic; }}
.wf-chips {{ display: flex; flex-wrap: wrap; gap: 5px; }}
.wf-chip {{ display: inline-flex; align-items: center; gap: 4px; padding: 3px 9px 3px 6px; border-radius: 999px;
  background: #FFF7E2; border: 1px solid #EBD28F; color: #6B4E00; font-size: .72rem; font-weight: 700; }}
.wf-chip svg {{ height: 14px; width: auto; color: #B8860B; }}
.wf-ttl {{ display: flex; align-items: center; gap: 8px; color: {GARNET}; font-weight: 800; font-size: .9rem; }}
.wf-ttl svg {{ height: 24px; width: auto; color: #B8860B; }}

@media (max-width: 900px) {{
  .wf-room {{ grid-template-columns: 1fr; }}
  .wf-room .photo {{ min-height: 420px; }}
  .wf-room .panel {{ padding: 26px 22px; }}
  .wf-tgrid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
}}
@media (max-width: 760px) {{
  .wf-hero {{ padding: 22px; background: linear-gradient(160deg, {GREEN} 0%, {GREEN} 60%, {GARNET} 60.3%); }}
  .wf-hero p {{ max-width: 100%; }} .wf-hero .stripe {{ display:none; }}
  .wf-cal .d {{ min-height: 44px; }} .wf-cal .d a {{ font-size: .62rem; }}
  .wf-cards {{ grid-template-columns: repeat(2, 1fr); }}
  .wf-topbar .tag {{ display: none; }}
  .wf-lockup.lg .name b, .wf-lockup.lg .name i {{ font-size: 1.6rem; }}
  .wf-legends {{ grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }}
  .wf-leg .ph {{ height: 190px; }}
  .st-key-home_tabs [data-baseweb="tab"] {{ padding: 14px 14px 12px; }}
}}
</style>
"""


def inject() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def badge(text: str, kind: str = "") -> str:
    return f'<span class="wf-badge {kind}">{text}</span>'


def status_badge(status: str | None) -> str:
    from database.models import LABELS
    kind = {"verificado": "ok", "confirmado": "ok", "nao_verificado": "warn", "inferido": "warn",
            "nao_confirmado": "warn", "divergente": "bad", "rejeitado": "bad"}.get(status or "", "")
    label = LABELS.get(status or "", "Inferido" if status == "inferido" else (status or "—"))
    return badge(label, kind)
