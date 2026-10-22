"""
McDuck · asistente financiero
Ejecutar:  streamlit run app.py
"""

import hmac
import os
import re

import streamlit as st
from dotenv import load_dotenv

st.set_page_config(page_title="McDuck · Asistente financiero", page_icon="🪙",
                   layout="wide", initial_sidebar_state="collapsed")

# ----------------------------------------------------------------------
# Configuración: .env en tu computador, Secrets en Streamlit Cloud.
# Todo termina en variables de entorno para que el resto del código
# (intermediate_tools.py, market_data.py) las lea con os.environ.get().
# ----------------------------------------------------------------------
load_dotenv()
for _name in ("GROQ_API_KEY", "ALPHA_VANTAGE_API_KEY", "SUPABASE_URL",
              "SUPABASE_KEY", "APP_PASSWORD", "DEFAULT_USER_ID"):
    try:
        if _name in st.secrets:
            os.environ[_name] = str(st.secrets[_name])
    except Exception:       # no hay secrets.toml: se usa solo el .env
        pass

import agent                                                    # noqa: E402
import market_data as md                                        # noqa: E402
import ui                                                       # noqa: E402
from intermediate_tools import AVISO_NO_ASESORIA, IntermediateTools, clasificar_riesgo  # noqa: E402
from memory import LocalMemory, SupabaseMemory, make_supabase_client  # noqa: E402

GROQ_KEY = os.environ.get("GROQ_API_KEY")
SUPA_URL = os.environ.get("SUPABASE_URL")
SUPA_KEY = os.environ.get("SUPABASE_KEY")

ui.inject_css(st)


# ----------------------------------------------------------------------
# Acceso opcional con contraseña (recomendado si publicas la app)
# ----------------------------------------------------------------------
def require_password() -> None:
    expected = os.environ.get("APP_PASSWORD")
    if not expected or st.session_state.get("authed"):
        return
    st.markdown(ui.header_html([]), unsafe_allow_html=True)
    pwd = st.text_input("Contraseña de acceso", type="password")
    if pwd:
        if hmac.compare_digest(pwd, expected):
            st.session_state["authed"] = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta.")
    st.stop()


require_password()


# ----------------------------------------------------------------------
# Recursos y datos en caché
# ----------------------------------------------------------------------
@st.cache_resource
def get_groq(key: str):
    from groq import Groq
    return Groq(api_key=key)


@st.cache_resource
def get_supabase(url: str, key: str):
    return make_supabase_client(url, key)


@st.cache_data(ttl=300, show_spinner=False)
def cached_quotes(symbols: tuple):
    return md.get_quotes(symbols)


@st.cache_data(ttl=900, show_spinner=False)
def cached_history(symbol: str):
    return md.get_history(symbol)


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def _overview_ok(symbol: str):
    # Si falla lanza excepción: Streamlit no cachea excepciones, así un error
    # temporal (límite de Alpha Vantage) no se queda guardado seis horas.
    r = IntermediateTools().consultar_indicadores_empresa(symbol)
    if "error" in r:
        raise RuntimeError(r["error"])
    return r


def get_overview(symbol: str):
    try:
        return _overview_ok(symbol), None
    except Exception as e:
        return None, str(e)


# ----------------------------------------------------------------------
# Memoria
# La app es de un solo perfil: toda la memoria se guarda bajo el mismo
# identificador (DEFAULT_USER_ID, o "invitado" si no lo defines).
# Si abres la app con ?u=otro_nombre usa una memoria aparte para ese nombre.
# ----------------------------------------------------------------------
def slug(texto: str) -> str:
    return re.sub(r"[^a-z0-9_-]", "", texto.lower().strip())[:40]


def init_memory(uid: str):
    """Devuelve (memoria, aviso). Cae a memoria temporal si Supabase falla."""
    supa = get_supabase(SUPA_URL, SUPA_KEY) if (SUPA_URL and SUPA_KEY) else None
    if supa is not None:
        mem = SupabaseMemory(supa, uid)
        try:
            mem.facts()      # prueba de conexión y de que las tablas existen
            return mem, None
        except Exception as e:
            aviso = ("No pude leer Supabase. Revisa SUPABASE_URL, SUPABASE_KEY y que hayas "
                     f"ejecutado supabase_schema.sql. Detalle: {e}")
    else:
        aviso = "Supabase no está configurado: la memoria es temporal y se pierde al cerrar la app."
    store = st.session_state.setdefault(f"local_{uid}", {"messages": [], "facts": {}})
    return LocalMemory(uid, store=store), aviso


uid = slug(st.query_params.get("u") or os.environ.get("DEFAULT_USER_ID") or "invitado") or "invitado"
memory, memory_warning = init_memory(uid)

hist_key, facts_key = f"hist_{uid}", f"facts_{uid}"
if hist_key not in st.session_state:
    try:
        st.session_state[hist_key] = memory.history(100)
        st.session_state[facts_key] = memory.facts()
    except Exception:
        st.session_state[hist_key], st.session_state[facts_key] = [], {}


# ----------------------------------------------------------------------
# Banner fijo de cotizaciones y encabezado
# ----------------------------------------------------------------------
todos = tuple(md.POPULARES) + tuple(md.INDICES)
quotes_all, quotes_src = cached_quotes(todos)
q_by_symbol = {q["symbol"]: q for q in quotes_all}
q_pop = [q_by_symbol[s] for s in md.POPULARES if s in q_by_symbol]

st.markdown(ui.ticker_html(q_pop, demo=(quotes_src == "demo")), unsafe_allow_html=True)
st.markdown(ui.header_html([
    ("Datos en vivo", "ok") if quotes_src != "demo" else ("Datos de demostración", "warn"),
    ("Memoria permanente", "ok") if memory.persistent else ("Memoria temporal", "warn"),
    ("IA conectada", "ok") if GROQ_KEY else ("IA sin clave", "bad"),
]), unsafe_allow_html=True)

tab_mercado, tab_chat = st.tabs(["Mercado", "Asistente"])


# ======================================================================
# MERCADO
# ======================================================================
with tab_mercado:
    if quotes_src == "demo":
        st.warning("No hay conexión con el proveedor de datos. Los precios que ves son de demostración, "
                   "no cotizaciones reales.")
    else:
        st.caption("Datos de Yahoo Finance con posible retraso. El panel se actualiza cada 5 minutos.")

    st.markdown('<div class="sec">Índices</div>', unsafe_allow_html=True)
    cols = st.columns(len(md.INDICES))
    for col, (sym, nombre) in zip(cols, md.INDICES.items()):
        col.markdown(ui.index_card_html(nombre, q_by_symbol.get(sym), neutral=(sym == "^VIX")),
                     unsafe_allow_html=True)

    st.markdown('<div class="sec">Una empresa en detalle</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
    elegido = c1.selectbox("Empresa popular", md.POPULARES, index=0)
    otro = c2.text_input("O escribe otro ticker", placeholder="Ej. NFLX, SPY, BRK-B").upper().strip()
    rango = c3.segmented_control("Periodo", list(ui.RANGOS), default="6M", help="M = meses, A = año") or "6M"
    tipo = c4.segmented_control("Gráfico", ["Línea", "Velas"], default="Línea") or "Línea"

    symbol = otro if re.fullmatch(r"[A-Z0-9.\-^]{1,10}", otro or "") else elegido
    if otro and symbol != otro:
        st.caption("Ese ticker no es válido; se muestra la empresa elegida en la lista.")

    with st.spinner(f"Cargando {symbol}..."):
        df, hist_src = cached_history(symbol)

    ultimo, previo = float(df["Close"].iloc[-1]), float(df["Close"].iloc[-2])
    k1, k2, k3, k4 = st.columns(4)
    k1.metric(f"{symbol} · último cierre", f"${ultimo:,.2f}", f"{(ultimo / previo - 1) * 100:+.2f}%")
    k2.metric("Máximo 52 semanas", f"${df['High'].tail(252).max():,.2f}")
    k3.metric("Mínimo 52 semanas", f"${df['Low'].tail(252).min():,.2f}")
    k4.metric("Volumen medio (30 días)", md.fmt_big(df["Volume"].tail(30).mean()))
    if hist_src == "demo" and quotes_src != "demo":     # si todo es demo, ya se avisó arriba
        st.warning(f"No pude obtener el histórico real de {symbol}. El gráfico es de demostración.")

    g1, g2 = st.columns([7, 4])
    with g1:
        st.markdown(f'<div class="sec">{symbol}: precio y volumen</div>', unsafe_allow_html=True)
        st.plotly_chart(ui.price_chart(df, ui.RANGOS[rango], tipo), width="stretch",
                        config={"displayModeBar": False})
    with g2:
        st.markdown('<div class="sec">Variación de hoy</div>', unsafe_allow_html=True)
        if q_pop:
            st.plotly_chart(ui.movers_chart(q_pop), width="stretch", config={"displayModeBar": False})

    st.markdown('<div class="sec">Indicadores de la empresa</div>', unsafe_allow_html=True)
    ov, ov_err = get_overview(symbol)
    if ov:
        try:
            dy = md.fmt_num(float(ov["dividend_yield"]) * 100, 2, " %")
        except (TypeError, ValueError):       # Alpha Vantage devuelve "None" o "-" si no hay dato
            dy = "—"
        f1, f2, f3, f4, f5 = st.columns(5)
        f1.metric("P/E", md.fmt_num(ov.get("pe_ratio")), help="Precio / utilidad por acción")
        f2.metric("EPS", md.fmt_num(ov.get("eps")), help="Utilidad por acción")
        f3.metric("Beta", md.fmt_num(ov.get("beta")), help="Sensibilidad frente al mercado. Más de 1 se mueve más que el mercado")
        f4.metric("Capitalización", md.fmt_big(ov.get("market_cap")), help="T = billones, MM = miles de millones, M = millones")
        f5.metric("Dividendo", dy, help="Rendimiento anual por dividendos")
        st.markdown(ui.verdict_html(clasificar_riesgo(ov.get("beta"), ov.get("pe_ratio")),
                                    ov.get("beta"), ov.get("pe_ratio"), AVISO_NO_ASESORIA),
                    unsafe_allow_html=True)
        st.caption(f"{ov.get('nombre') or symbol} · sector: {ov.get('sector') or 'sin dato'} · Fuente: Alpha Vantage.")
    else:
        st.info(f"No hay indicadores disponibles para {symbol} ahora mismo. {ov_err}")


# ======================================================================
# ASISTENTE (chat + memoria)
# ======================================================================
# El asistente usa el avatar por defecto de Streamlit: así el CSS puede reconocer sus mensajes
AVATAR = {"user": {"avatar": ":material/person:"}, "assistant": {}}


def queue_prompt(texto: str) -> None:
    st.session_state["pending_prompt"] = texto


def popover(col, label: str, **kwargs):
    """Popover que ocupa todo el ancho de su columna (si esta versión de Streamlit lo permite)."""
    try:
        return col.popover(label, width="stretch", **kwargs)
    except TypeError:
        return col.popover(label, **kwargs)


def refresh_facts() -> None:
    st.session_state[facts_key] = memory.facts()


def memory_panel() -> None:
    """Contenido del botón «Memoria»: ver, agregar y quitar lo que McDuck recuerda."""
    facts = st.session_state[facts_key]
    st.markdown("**Lo que McDuck recuerda de ti**")
    if not facts:
        st.caption("Todavía no hay datos guardados. McDuck guarda lo que le pidas que recuerde, "
                   "o puedes agregarlo aquí.")
    for k, v in facts.items():
        a, b = st.columns([2.4, 1.7])
        a.markdown(f"**{k.replace('_', ' ')}**  \n{v}")
        if b.button("Quitar", key=f"del_{k}"):
            memory.delete_fact(k)
            refresh_facts()
            st.rerun()
    with st.form("nuevo_dato", clear_on_submit=True):
        k_new = st.text_input("Dato", placeholder="nombre")
        v_new = st.text_input("Valor", placeholder="Rafa")
        if st.form_submit_button("Guardar dato") and k_new.strip() and v_new.strip():
            memory.save_fact(k_new, v_new)
            refresh_facts()
            st.rerun()


with tab_chat:
    historial = st.session_state[hist_key]

    if not GROQ_KEY:
        st.error("Falta GROQ_API_KEY. Agrégala en tu archivo .env (o en Secrets si la app está publicada).")
    if memory_warning and not memory.persistent:
        st.caption(memory_warning)

    # Barra de acciones del chat
    _, col_mem, col_clear = st.columns([6, 1.6, 2.4])
    with popover(col_mem, "Memoria", icon=":material/psychology:"):
        memory_panel()
    with popover(col_clear, "Borrar conversación", icon=":material/delete:", disabled=not historial):
        st.write("Se borra el historial de este chat. Lo que McDuck recuerda de ti se conserva.")
        if st.button("Sí, borrar conversación", type="primary", key="confirm_clear"):
            memory.clear_history()
            st.session_state[hist_key] = []
            st.rerun()

    chat_box = st.container()          # aquí van TODOS los mensajes, incluido el turno nuevo
    prompt = st.chat_input("Pregunta por una empresa...", disabled=not GROQ_KEY) or st.session_state.pop("pending_prompt", None)

    with chat_box:
        if not historial and not prompt:
            st.markdown(ui.empty_chat_html(st.session_state[facts_key].get("nombre")), unsafe_allow_html=True)
            ejemplos = {"Precio de AAPL": "¿Cuál es el precio actual de AAPL?",
                        "Cierre de MSFT": "¿Cuánto cerró ayer MSFT?",
                        "Histórico de NVDA": "Dame los últimos cierres de NVDA.",
                        "Indicadores de TSLA": "¿Qué indicadores básicos tiene TSLA?",
                        "¿Apple es estable?": "¿Apple parece una empresa estable o riesgosa?"}
            for col, (etiqueta, pregunta) in zip(st.columns(len(ejemplos)), ejemplos.items()):
                col.button(etiqueta, on_click=queue_prompt, args=(pregunta,), width="stretch", key=f"ej_{etiqueta}")

        for m in historial:
            with st.chat_message(m["role"], **AVATAR[m["role"]]):
                st.write(m["content"])
                if m.get("tools"):
                    st.markdown("".join(f'<span class="chip">{t}</span>' for t in m["tools"]), unsafe_allow_html=True)

        if prompt and GROQ_KEY:
            with st.chat_message("user", **AVATAR["user"]):
                st.write(prompt)
            with st.chat_message("assistant", **AVATAR["assistant"]):
                try:
                    with st.spinner("McDuck está consultando..."):
                        respuesta, usadas = agent.run_agent(get_groq(GROQ_KEY), memory, prompt)
                    st.write(respuesta)
                    if usadas:
                        st.markdown("".join(f'<span class="chip">{t}</span>' for t in usadas), unsafe_allow_html=True)
                    historial.append({"role": "user", "content": prompt})
                    historial.append({"role": "assistant", "content": respuesta, "tools": usadas})
                    refresh_facts()          # por si guardó o borró un dato
                except Exception as e:
                    st.error(f"No pude completar la consulta: {e}")

st.markdown('<div class="foot">Proyecto educativo. La información no constituye asesoría financiera.</div>',
            unsafe_allow_html=True)
