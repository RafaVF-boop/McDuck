"""
Piezas visuales de McDuck: estilos, banner de cotizaciones, encabezado,
tarjetas de índices y gráficos. Sin lógica de negocio.

Identidad: terminal financiera de noche. Azul casi negro, bordes finos que
brillan apenas, y una sola moneda dorada (la marca) como acento.
El dorado es el único color de interfaz; el cian solo aparece como luz de fondo.
"""

import html

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- Paleta -------------------------------------------------------------
BG = "#070B14"          # fondo de la página
SURFACE = "#0E1626"     # tarjetas y gráficos
SURFACE_2 = "#131E33"   # mensajes del usuario, controles
LINE = "#1F2D47"        # bordes y rejillas
TEXT = "#E6ECF5"        # texto principal
MUTED = "#8FA0BA"       # texto secundario
GOLD = "#F4B942"        # marca y acento de interfaz
UP = "#34D399"          # sube (siempre con ▲ o signo +)
DOWN = "#F87171"        # baja (siempre con ▼ o signo -)

# Series del gráfico de precios (validadas en modo oscuro: banda de luminosidad,
# separación para daltonismo y contraste contra la superficie)
S1, S2, S3 = "#3987e5", "#c28500", "#9085e9"

FONT = "IBM Plex Sans, system-ui, sans-serif"


# ----------------------------------------------------------------------
# CSS global
# ----------------------------------------------------------------------
CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@500;600;800&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

:root {{
  --bg:{BG}; --surface:{SURFACE}; --surface-2:{SURFACE_2}; --line:{LINE};
  --text:{TEXT}; --muted:{MUTED}; --gold:{GOLD}; --up:{UP}; --down:{DOWN};
  --ticker-h: 42px;
}}

/* Fondo: luz tenue arriba y una rejilla casi invisible */
.stApp {{
  background:
    radial-gradient(900px 420px at 80% -8%, rgba(56,217,245,.10), transparent 60%),
    radial-gradient(700px 380px at 6% 0%, rgba(244,185,66,.07), transparent 55%),
    linear-gradient(rgba(143,160,186,.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(143,160,186,.035) 1px, transparent 1px),
    var(--bg);
  background-size: auto, auto, 44px 44px, 44px 44px, auto;
  color: var(--text);
}}
.stApp, .stMarkdown, .stTextInput input, .stSelectbox, .stButton button,
.stTabs button, [data-testid="stMetric"], [data-testid="stChatMessage"],
[data-testid="stChatInput"] textarea, [data-testid="stPopover"] button {{
  font-family: 'IBM Plex Sans', system-ui, sans-serif;
}}

/* No hay barra lateral */
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"] {{ display: none; }}

/* El banner va fijo arriba; el contenido baja su altura */
[data-testid="stHeader"] {{ top: var(--ticker-h); background: transparent; }}
.block-container {{ padding-top: calc(var(--ticker-h) + 2.4rem); max-width: 1240px; }}

/* ---------- Banner de cotizaciones (se mueve de izquierda a derecha) ---------- */
.ticker {{
  position: fixed; top: 0; left: 0; right: 0; height: var(--ticker-h);
  z-index: 1000000; background: #050912; color: var(--text); overflow: hidden;
  display: flex; align-items: center;
  box-shadow: 0 1px 0 rgba(244,185,66,.55), 0 8px 28px rgba(56,217,245,.07);
}}
.ticker-flag {{
  flex: none; z-index: 2; padding: 0 16px; height: 100%; display: flex; align-items: center;
  background: var(--gold); color: #1A1202; font-weight: 600; font-size: 12.5px;
}}
.ticker-window {{ overflow: hidden; flex: 1; }}
.ticker-track {{
  display: flex; width: max-content;
  animation: ticker-ltr var(--ticker-secs, 60s) linear infinite;
}}
.ticker:hover .ticker-track {{ animation-play-state: paused; }}
@keyframes ticker-ltr {{            /* izquierda -> derecha */
  from {{ transform: translateX(-50%); }}
  to   {{ transform: translateX(0); }}
}}
.tk {{ display: inline-flex; align-items: baseline; gap: 9px; padding: 0 22px;
      font-size: 14px; white-space: nowrap; font-variant-numeric: tabular-nums; }}
.tk b {{ font-weight: 600; letter-spacing: .02em; color: var(--text); }}
.tk .px {{ color: var(--muted); }}
.tk .up {{ color: var(--up); }}
.tk .dn {{ color: var(--down); }}
.tk::after {{ content: ""; width: 1px; height: 14px; background: var(--line); margin-left: 22px; align-self: center; }}
@media (prefers-reduced-motion: reduce) {{
  .ticker-track {{ animation: none; }}
  .ticker-window {{ overflow-x: auto; }}
}}

/* ---------- Encabezado ---------- */
.hdr {{ display: flex; justify-content: space-between; align-items: center;
       flex-wrap: wrap; gap: 14px 24px; margin: 0 0 1.2rem; }}
.brand {{ display: flex; align-items: center; gap: 14px; }}
.coin {{ width: 34px; height: 34px; border-radius: 50%; flex: none; position: relative;
        background: radial-gradient(circle at 34% 28%, #FFE9A8, #F4B942 52%, #B9810F);
        box-shadow: 0 0 22px rgba(244,185,66,.40); }}
.coin::after {{ content: ""; position: absolute; inset: 6px; border-radius: 50%;
               border: 2px solid rgba(90,56,0,.55); }}
.brand-name {{ font-family: 'Sora', sans-serif; font-weight: 800; font-size: 2.2rem;
              letter-spacing: -.03em; color: var(--text); line-height: 1; }}
.brand-sub {{ color: var(--muted); font-size: .98rem; margin-left: 2px; }}

.pills {{ display: flex; flex-wrap: wrap; gap: 8px; }}
.pill {{ display: inline-flex; align-items: center; gap: 8px; padding: 5px 12px; font-size: .8rem;
        color: var(--muted); background: rgba(14,22,38,.75); border: 1px solid var(--line);
        border-radius: 999px; }}
.dot {{ width: 7px; height: 7px; border-radius: 50%; }}
.dot.ok {{ background: var(--up); box-shadow: 0 0 8px var(--up); }}
.dot.warn {{ background: var(--gold); box-shadow: 0 0 8px var(--gold); }}
.dot.bad {{ background: var(--down); box-shadow: 0 0 8px var(--down); }}

/* ---------- Pestañas ---------- */
.stTabs [data-baseweb="tab-list"] {{ gap: 8px; border-bottom: 1px solid var(--line); }}
.stTabs [data-baseweb="tab"] {{ font-weight: 500; color: var(--muted); }}
.stTabs [aria-selected="true"] {{ color: var(--text); font-weight: 600; }}
.stTabs [data-baseweb="tab-highlight"] {{ background-color: var(--gold); height: 3px; }}

/* ---------- Títulos de sección ---------- */
.sec {{ font-family: 'Sora', sans-serif; font-weight: 600; font-size: 1.05rem;
       color: var(--text); margin: 1.5rem 0 .6rem; }}

/* ---------- Tarjetas ---------- */
.idx, [data-testid="stMetric"], .verdict {{
  background: linear-gradient(180deg, rgba(19,30,51,.85), rgba(14,22,38,.9));
  border: 1px solid var(--line); border-radius: 10px;
  box-shadow: 0 10px 28px rgba(0,0,0,.28);
}}
.idx {{ padding: 12px 14px 10px; }}
.idx-name {{ color: var(--muted); font-size: .85rem; }}
.idx-val {{ font-size: 1.45rem; font-weight: 600; color: var(--text);
           font-variant-numeric: tabular-nums; margin-top: 2px; }}
.idx-row {{ display: flex; justify-content: space-between; align-items: flex-end; }}
.chg {{ font-size: .9rem; font-weight: 500; font-variant-numeric: tabular-nums; }}
.chg.up {{ color: var(--up); }} .chg.dn {{ color: var(--down); }} .chg.nt {{ color: var(--muted); }}

[data-testid="stMetric"] {{ padding: 10px 14px; }}
[data-testid="stMetricLabel"] {{ color: var(--muted); }}
[data-testid="stMetricValue"] {{ font-variant-numeric: tabular-nums; color: var(--text); font-size: 1.75rem; }}

.verdict {{ padding: 14px 16px; margin-top: .8rem; }}
.verdict .lbl {{ color: var(--muted); font-size: .85rem; }}
.verdict .val {{ font-family: 'Sora', sans-serif; font-weight: 800; font-size: 1.6rem; margin: 2px 0 6px; }}
.verdict .val.estable {{ color: var(--up); }} .verdict .val.moderada {{ color: var(--gold); }}
.verdict .val.riesgosa {{ color: var(--down); }} .verdict .val.nd {{ color: var(--muted); }}
.verdict p {{ margin: 0; color: var(--muted); font-size: .88rem; line-height: 1.5; }}

/* Gráficos dentro de una tarjeta */
[data-testid="stPlotlyChart"] {{ border: 1px solid var(--line); border-radius: 10px; overflow: hidden;
                                background: var(--surface); box-shadow: 0 10px 28px rgba(0,0,0,.28); }}

/* ---------- Botones y controles ---------- */
.stButton button, [data-testid="stPopover"] > button {{
  background: rgba(19,30,51,.7); color: var(--text); border: 1px solid var(--line); border-radius: 8px;
  transition: border-color .15s, box-shadow .15s;
}}
.stButton button:hover, [data-testid="stPopover"] > button:hover {{
  border-color: var(--gold); color: var(--text); box-shadow: 0 0 0 1px rgba(244,185,66,.35);
}}
.stButton button[kind="primary"] {{ background: var(--gold); color: #1A1202; border-color: var(--gold); font-weight: 600; }}
.stTextInput input, [data-baseweb="select"] > div {{ background: var(--surface-2); border-color: var(--line); }}

/* ---------- Chat ---------- */
.empty {{ text-align: center; padding: 2.6rem 0 1.2rem; }}
.empty h2 {{ font-family: 'Sora', sans-serif; font-weight: 600; font-size: 1.9rem; margin: 0 0 .3rem; color: var(--text); }}
.empty p {{ color: var(--muted); margin: 0; font-size: 1.05rem; }}
.chip {{ display: inline-block; font-size: .78rem; color: var(--muted); background: rgba(19,30,51,.9);
        border: 1px solid var(--line); border-radius: 999px; padding: 2px 10px; margin: 6px 6px 0 0; }}
[data-testid="stChatMessage"] {{ background: var(--surface); border: 1px solid var(--line); border-radius: 10px; }}
[data-testid="stChatMessage"]:not(:has([data-testid="stChatMessageAvatarAssistant"])) {{ background: var(--surface-2); }}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {{ border-left: 3px solid var(--gold); }}
[data-testid="stChatInput"] {{ border: 1px solid var(--line); border-radius: 12px; background: var(--surface); }}
[data-testid="stChatInput"]:focus-within {{ border-color: var(--gold); box-shadow: 0 0 0 1px rgba(244,185,66,.35), 0 0 24px rgba(244,185,66,.12); }}

.foot {{ text-align: center; color: var(--muted); font-size: .8rem; margin: 2.4rem 0 .4rem; opacity: .8; }}
</style>
"""


def inject_css(st) -> None:
    st.markdown(CSS, unsafe_allow_html=True)


# ----------------------------------------------------------------------
# Banner de cotizaciones
# ----------------------------------------------------------------------
def ticker_html(quotes: list[dict], demo: bool = False) -> str:
    if not quotes:
        return ""
    items = []
    for q in quotes:
        sube = q["pct"] >= 0
        flecha = "▲" if sube else "▼"
        items.append(
            f'<span class="tk"><b>{html.escape(q["symbol"])}</b>'
            f'<span class="px">{q["price"]:,.2f}</span>'
            f'<span class="{"up" if sube else "dn"}">{flecha} {abs(q["pct"]):.2f}%</span></span>'
        )
    una_vuelta = "".join(items)
    segundos = max(30, len(items) * 5)         # velocidad constante sin importar cuántas haya
    flag = '<div class="ticker-flag">Datos de demostración</div>' if demo else ""
    return (
        f'<div class="ticker" style="--ticker-secs:{segundos}s">{flag}'
        f'<div class="ticker-window"><div class="ticker-track">'
        f'{una_vuelta}{una_vuelta}</div></div></div>'
    )


# ----------------------------------------------------------------------
# Encabezado con estado
# ----------------------------------------------------------------------
def header_html(pills: list[tuple[str, str]]) -> str:
    """pills: lista de (texto, estado) con estado 'ok', 'warn' o 'bad'."""
    chips = "".join(
        f'<span class="pill"><span class="dot {estado}"></span>{html.escape(texto)}</span>'
        for texto, estado in pills
    )
    return (
        '<div class="hdr"><div class="brand"><span class="coin"></span>'
        '<span class="brand-name">McDuck</span>'
        '<span class="brand-sub">Asistente financiero con IA</span></div>'
        f'<div class="pills">{chips}</div></div>'
    )


def empty_chat_html(nombre: str | None) -> str:
    titulo = f"Hola, {html.escape(nombre)}." if nombre else "Hola, soy McDuck."
    return f'<div class="empty"><h2>{titulo}</h2><p>¿Qué empresa quieres revisar hoy?</p></div>'


# ----------------------------------------------------------------------
# Tarjeta de índice con mini gráfico
# ----------------------------------------------------------------------
def _sparkline(values: list[float], color: str, w: int = 104, h: int = 38) -> str:
    if len(values) < 2:
        return ""
    lo, hi = min(values), max(values)
    rango = (hi - lo) or 1
    pts = [(i * w / (len(values) - 1), h - 4 - (v - lo) / rango * (h - 8)) for i, v in enumerate(values)]
    linea = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"0,{h} {linea} {w},{h}"
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" aria-hidden="true">'
            f'<polygon points="{area}" fill="{color}" fill-opacity="0.14"/>'
            f'<polyline points="{linea}" fill="none" stroke="{color}" stroke-width="2" '
            f'stroke-linejoin="round" stroke-linecap="round"/></svg>')


def index_card_html(name: str, q: dict | None, neutral: bool = False) -> str:
    if not q:
        return f'<div class="idx"><div class="idx-name">{html.escape(name)}</div><div class="idx-val">—</div></div>'
    sube = q["pct"] >= 0
    if neutral:      # el VIX sube cuando hay miedo: no se pinta "bueno/malo"
        cls, color = "nt", MUTED
    else:
        cls, color = ("up", UP) if sube else ("dn", DOWN)
    flecha = "▲" if sube else "▼"
    return (
        f'<div class="idx"><div class="idx-name">{html.escape(name)}</div>'
        f'<div class="idx-row"><div>'
        f'<div class="idx-val">{q["price"]:,.2f}</div>'
        f'<div class="chg {cls}">{flecha} {abs(q["pct"]):.2f}%</div></div>'
        f'{_sparkline(q["spark"], color)}</div></div>'
    )


def verdict_html(evaluacion: str, beta, pe, aviso: str) -> str:
    clase = {"estable": "estable", "moderada": "moderada", "riesgosa": "riesgosa"}.get(evaluacion, "nd")
    texto = evaluacion.capitalize()
    return (
        f'<div class="verdict"><div class="lbl">Evaluación básica</div>'
        f'<div class="val {clase}">{html.escape(texto)}</div>'
        f'<p>Según beta ({html.escape(str(beta))}) y P/E ({html.escape(str(pe))}). '
        f'{html.escape(aviso)}</p></div>'
    )


# ----------------------------------------------------------------------
# Gráficos (Plotly)
# ----------------------------------------------------------------------
def _base_layout(fig: go.Figure, height: int) -> None:
    fig.update_layout(
        height=height, margin=dict(l=8, r=8, t=12, b=4),
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        font=dict(family=FONT, color=MUTED, size=12),
        hovermode="x unified",
        legend=dict(orientation="h", x=0, y=1.08, bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT)),
        hoverlabel=dict(font_family=FONT, bgcolor=SURFACE_2, bordercolor=LINE, font_color=TEXT),
    )
    fig.update_xaxes(showgrid=False, linecolor=LINE, zeroline=False)
    fig.update_yaxes(gridcolor=LINE, zeroline=False)


RANGOS = {"1M": 21, "3M": 63, "6M": 126, "1A": 252}   # meses y año


def price_chart(df: pd.DataFrame, dias: int, tipo: str) -> go.Figure:
    d = df.copy()
    d["MA20"] = d["Close"].rolling(20).mean()    # se calculan con todo el año
    d["MA50"] = d["Close"].rolling(50).mean()    # y luego se recorta al rango pedido
    d = d.tail(dias)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.78, 0.22], vertical_spacing=0.03)
    if tipo == "Velas":
        # Sube = vela hueca, baja = vela rellena: no depende solo del color
        fig.add_trace(go.Candlestick(
            x=d.index, open=d["Open"], high=d["High"], low=d["Low"], close=d["Close"],
            name="Precio", increasing_line_color=UP, decreasing_line_color=DOWN,
            increasing_fillcolor=SURFACE, decreasing_fillcolor=DOWN), row=1, col=1)
    else:
        fig.add_trace(go.Scatter(
            x=d.index, y=d["Close"], name="Cierre", mode="lines",
            line=dict(color=S1, width=2.2),
            hovertemplate="%{y:$,.2f}"), row=1, col=1)
    fig.add_trace(go.Scatter(x=d.index, y=d["MA20"], name="Media 20 días", mode="lines",
                             line=dict(color=S2, width=1.75), hovertemplate="%{y:$,.2f}"), row=1, col=1)
    fig.add_trace(go.Scatter(x=d.index, y=d["MA50"], name="Media 50 días", mode="lines",
                             line=dict(color=S3, width=1.75, dash="dash"), hovertemplate="%{y:$,.2f}"), row=1, col=1)
    fig.add_trace(go.Bar(x=d.index, y=d["Volume"], name="Volumen", marker_color="#2C3E63",
                         showlegend=False, hovertemplate="%{y:,.0f}"), row=2, col=1)

    _base_layout(fig, 470)
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])], rangeslider_visible=False)
    fig.update_yaxes(tickprefix="$", row=1, col=1)
    fig.update_yaxes(title_text="Volumen", title_font_size=11, tickformat=".2s", row=2, col=1)
    return fig


def movers_chart(quotes: list[dict]) -> go.Figure:
    q = sorted(quotes, key=lambda x: x["pct"])
    fig = go.Figure(go.Bar(
        x=[x["pct"] for x in q], y=[x["symbol"] for x in q], orientation="h",
        marker_color=[UP if x["pct"] >= 0 else DOWN for x in q],
        text=[f'{x["pct"]:+.2f}%' for x in q], textposition="outside", cliponaxis=False,
        textfont=dict(color=TEXT),
        hovertemplate="%{y}: %{x:+.2f}%<extra></extra>"))
    _base_layout(fig, 470)
    fig.update_layout(hovermode="closest", showlegend=False, margin=dict(l=8, r=44, t=12, b=4))
    pcts = [x["pct"] for x in q]
    margen = (max(pcts) - min(pcts) or 1) * 0.38     # espacio para las etiquetas de los extremos
    fig.update_xaxes(ticksuffix="%", showgrid=True, gridcolor=LINE, zeroline=True,
                     zerolinecolor=MUTED, zerolinewidth=1,
                     range=[min(0, min(pcts)) - margen, max(0, max(pcts)) + margen])
    fig.update_yaxes(showgrid=False)
    return fig
