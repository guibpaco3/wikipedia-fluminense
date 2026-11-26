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

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&display=swap');
html, body, [class*="css"], .stMarkdown, .stText {{ font-family: Inter, system-ui, sans-serif; }}
h1, h2, h3 {{ font-family: 'Source Serif 4', Georgia, serif !important; color: {INK}; letter-spacing: -.01em; }}
.block-container {{ padding-top: 1.4rem; max-width: 1320px; }}
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

@media (max-width: 760px) {{
  .wf-hero {{ padding: 22px; background: linear-gradient(160deg, {GREEN} 0%, {GREEN} 60%, {GARNET} 60.3%); }}
  .wf-hero p {{ max-width: 100%; }} .wf-hero .stripe {{ display:none; }}
  .wf-cal .d {{ min-height: 44px; }} .wf-cal .d a {{ font-size: .62rem; }}
  .wf-cards {{ grid-template-columns: repeat(2, 1fr); }}
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
