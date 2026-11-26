"""Globo terrestre 3D (WebGL) com Globe.gl, integrado ao Streamlit via Components v2.

- Gira, aproxima/afasta e permite clicar nos países.
- Países com partidas recebem destaque verde + marcadores pulsantes.
- O país selecionado fica grená e a câmera voa suavemente até ele.
- O clique é devolvido ao Python como "trigger" (`country` = ISO alfa-2).
"""
from __future__ import annotations

import streamlit as st

GLOBE_JS_URL = "https://cdn.jsdelivr.net/npm/globe.gl@2.34.4/dist/globe.gl.min.js"
GEOJSON_URL = ("https://cdn.jsdelivr.net/gh/nvkelso/natural-earth-vector@v5.1.2/"
               "geojson/ne_110m_admin_0_countries.geojson")
IMG = "https://cdn.jsdelivr.net/npm/three-globe@2.31.0/example/img/"

HTML = """<div class="wf-globe-wrap"><div class="wf-globe"></div>
<div class="wf-globe-hint">Arraste para girar · role para aproximar · clique em um país</div>
<div class="wf-globe-legend"><span><i class="dot g"></i>Com partidas</span>
<span><i class="dot r"></i>Selecionado</span></div>
<div class="wf-globe-loading">Carregando o planeta…</div></div>"""

CSS = """
.wf-globe-wrap { position: relative; width: 100%; border-radius: 18px; overflow: hidden;
  background: radial-gradient(ellipse at center, #0e1f17 0%, #050807 70%);
  border: 1px solid #1f2b25; box-shadow: 0 20px 60px rgba(0,0,0,.45); }
.wf-globe { width: 100%; cursor: grab; }
.wf-globe:active { cursor: grabbing; }
.wf-globe-hint { position: absolute; left: 14px; bottom: 12px; font: 500 12px Inter, sans-serif;
  color: rgba(230,240,235,.7); background: rgba(5,10,8,.55); padding: 5px 10px; border-radius: 999px;
  pointer-events: none; }
.wf-globe-legend { position: absolute; right: 14px; bottom: 12px; display: flex; gap: 12px;
  font: 500 12px Inter, sans-serif; color: rgba(230,240,235,.85); background: rgba(5,10,8,.55);
  padding: 5px 10px; border-radius: 999px; pointer-events: none; }
.wf-globe-legend .dot { display:inline-block; width:9px; height:9px; border-radius:50%;
  margin-right:5px; vertical-align: -1px; }
.wf-globe-legend .dot.g { background:#2BD67B; box-shadow:0 0 8px #2BD67B; }
.wf-globe-legend .dot.r { background:#C8173F; box-shadow:0 0 8px #C8173F; }
.wf-globe-loading { position:absolute; inset:0; display:flex; align-items:center; justify-content:center;
  font: 600 14px Inter, sans-serif; color:#9AA8A1; pointer-events:none; }
.wf-tip { font: 500 13px Inter, sans-serif; background: rgba(10,15,13,.92); color: #fff;
  border: 1px solid #2BD67B55; border-radius: 10px; padding: 7px 11px; }
.wf-tip b { font-family: Oswald, Inter, sans-serif; font-size: 15px; letter-spacing: .03em; }
.wf-tip .n { color: #2BD67B; } .wf-tip .z { color: #9AA8A1; }
"""

JS = """
const GLOBE_JS = "%GLOBE_JS%";
const GEOJSON = "%GEOJSON%";
const IMG = "%IMG%";

function loadGlobeLib() {
  if (window.Globe) return Promise.resolve();
  if (!window.__wfGlobeLib) {
    window.__wfGlobeLib = new Promise((resolve, reject) => {
      const s = document.createElement('script');
      s.src = GLOBE_JS; s.async = true;
      s.onload = () => resolve(); s.onerror = () => reject(new Error('globe.gl'));
      document.head.appendChild(s);
    });
  }
  return window.__wfGlobeLib;
}
function loadGeo() {
  if (!window.__wfGeo) {
    window.__wfGeo = fetch(GEOJSON).then(r => r.json()).then(g => g.features
      .map(f => {
        const p = f.properties;
        let iso = p.ISO_A2_EH && p.ISO_A2_EH !== '-99' ? p.ISO_A2_EH : p.ISO_A2;
        return { ...f, iso, name: p.NAME_PT || p.NAME };
      })
      .filter(f => f.iso !== 'AQ'));
  }
  return window.__wfGeo;
}

function apply(state) {
  const { globe, data } = state;
  if (!globe) return;
  const counts = {};
  (data.points || []).forEach(p => counts[p.iso2] = p);
  const sel = data.selected;
  const hov = state.hovered;
  globe
    .polygonAltitude(d => d.iso === sel ? 0.07 : d === hov ? 0.035 : counts[d.iso] ? 0.014 : 0.006)
    .polygonCapColor(d => d.iso === sel ? 'rgba(200,23,63,0.88)'
        : d === hov ? (counts[d.iso] ? 'rgba(43,214,123,0.85)' : 'rgba(255,255,255,0.22)')
        : counts[d.iso] ? 'rgba(0,140,80,0.62)' : 'rgba(255,255,255,0.035)')
    .polygonSideColor(d => d.iso === sel ? 'rgba(122,0,25,0.6)' : 'rgba(0,60,35,0.25)')
    .polygonStrokeColor(d => d.iso === sel ? '#ffffff' : counts[d.iso] ? 'rgba(160,255,200,0.55)'
        : 'rgba(255,255,255,0.18)')
    .polygonLabel(d => {
      const c = counts[d.iso];
      const line = c ? `<span class="n">${c.total} partida${c.total > 1 ? 's' : ''}</span>`
                     : `<span class="z">Nenhuma partida registrada</span>`;
      return `<div class="wf-tip"><b>${d.name}</b><br>${line}</div>`;
    });
  const pts = data.points || [];
  const max = Math.max(1, ...pts.map(p => p.total));
  globe.pointsData(pts)
    .pointLat('lat').pointLng('lon')
    .pointColor(p => p.iso2 === sel ? '#ffffff' : '#2BD67B')
    .pointAltitude(p => 0.03 + 0.22 * Math.sqrt(p.total / max))
    .pointRadius(p => 0.35 + 0.5 * Math.sqrt(p.total / max))
    .pointLabel(p => `<div class="wf-tip"><b>${p.name}</b><br><span class="n">${p.total} partida${p.total > 1 ? 's' : ''}</span></div>`);
  globe.ringsData(pts.filter(p => p.iso2 !== 'BR' || pts.length === 1))
    .ringLat('lat').ringLng('lon')
    .ringColor(p => t => p.iso2 === sel ? `rgba(255,80,120,${1 - t})` : `rgba(43,214,123,${1 - t})`)
    .ringMaxRadius(p => 2 + 3 * Math.sqrt(p.total / max)).ringPropagationSpeed(1.4).ringRepeatPeriod(1700);

  const focusKey = data.focus ? `${sel}|${data.focus.lat}|${data.focus.lon}` : null;
  if (focusKey && focusKey !== state.lastFocus) {
    globe.controls().autoRotate = false;
    globe.pointOfView({ lat: data.focus.lat, lng: data.focus.lon, altitude: 1.55 }, 1600);
  } else if (!sel && state.lastFocus) {
    globe.pointOfView({ altitude: 2.3 }, 1200);
    globe.controls().autoRotate = true;
  }
  state.lastFocus = focusKey;
}

export default function (component) {
  const { data, parentElement, setTriggerValue } = component;
  const wrap = parentElement.querySelector('.wf-globe-wrap');
  const el = parentElement.querySelector('.wf-globe');
  let state = wrap.__wf;
  if (!state) {
    state = wrap.__wf = { data, globe: null, hovered: null, lastFocus: null };
    const height = data.height || 640;
    el.style.height = height + 'px';
    Promise.all([loadGlobeLib(), loadGeo()]).then(([_, features]) => {
      const globe = window.Globe({ animateIn: true })(el)
        .width(el.clientWidth || 800).height(height)
        .globeImageUrl(IMG + 'earth-blue-marble.jpg')
        .bumpImageUrl(IMG + 'earth-topology.png')
        .backgroundImageUrl(IMG + 'night-sky.png')
        .showAtmosphere(true).atmosphereColor('#6fe3a8').atmosphereAltitude(0.17)
        .polygonsData(features)
        .polygonsTransitionDuration(350)
        .onPolygonHover(h => { state.hovered = h; el.style.cursor = h ? 'pointer' : 'grab'; apply(state); })
        .onPolygonClick(d => setTriggerValue('country', d.iso))
        .onPointClick(p => setTriggerValue('country', p.iso2));
      globe.controls().autoRotate = !state.data.selected;
      globe.controls().autoRotateSpeed = 0.35;
      globe.controls().enableDamping = true;
      globe.pointOfView({ lat: -15, lng: -30, altitude: 2.3 });
      state.globe = globe;
      const loading = parentElement.querySelector('.wf-globe-loading');
      if (loading) loading.remove();
      state.ro = new ResizeObserver(() => { if (el.clientWidth) globe.width(el.clientWidth); });
      state.ro.observe(el);
      apply(state);
    }).catch(err => {
      const loading = parentElement.querySelector('.wf-globe-loading');
      if (loading) loading.textContent = 'Não foi possível carregar o globo 3D (' + err.message +
        '). Verifique a conexão com a internet.';
    });
  } else {
    state.data = data;
    apply(state);
  }
  return () => {
    // Libera o contexto WebGL apenas quando o componente sai de fato da página.
    setTimeout(() => {
      if (!wrap.isConnected && state.globe) {
        try { state.ro && state.ro.disconnect(); state.globe._destructor(); } catch (e) {}
        state.globe = null;
      }
    }, 0);
  };
}
"""

_globe = st.components.v2.component(
    "wf_globe",
    html=HTML,
    css=CSS,
    js=JS.replace("%GLOBE_JS%", GLOBE_JS_URL).replace("%GEOJSON%", GEOJSON_URL).replace("%IMG%", IMG),
    isolate_styles=False,
)


def render_globe(points: list[dict], selected: str | None, focus: dict | None,
                 height: int = 640, key: str = "wf_globe") -> str | None:
    """Desenha o globo e devolve o ISO alfa-2 do país clicado nesta execução (ou None)."""
    result = _globe(
        key=key,
        data={"points": points, "selected": selected, "focus": focus, "height": height},
        on_country_change=lambda: None,
    )
    return getattr(result, "country", None) if result is not None else None
