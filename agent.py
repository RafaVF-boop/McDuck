"""
Cerebro de McDuck: prompt, herramientas y bucle de llamadas al modelo.
No depende de Streamlit; recibe un cliente de Groq y un objeto de memoria
(SupabaseMemory o LocalMemory), así que también se puede probar desde consola.
"""

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from intermediate_tools import IntermediateTools

MODEL = "openai/gpt-oss-120b"
MAX_TOOL_ROUNDS = 6      # tope de vueltas modelo<->herramientas, evita bucles infinitos


def build_system_prompt(facts: dict) -> str:
    ahora = datetime.now(ZoneInfo("America/Guatemala")).strftime("%A %d/%m/%Y %H:%M")

    if facts:
        recordado = "\n".join(f"- {k}: {v}" for k, v in facts.items())
    else:
        recordado = "- (todavía no sabes nada del usuario)"

    return f"""
Te llamas McDuck, un asistente financiero que habla en español, tutea al usuario y responde de manera breve, clara y práctica.
Fecha y hora actual (Guatemala): {ahora}.

Lo que ya sabes del usuario (memoria permanente):
{recordado}

Usa estos datos con naturalidad, por ejemplo llamándolo por su nombre. No los repitas si no hace falta.

Herramientas de mercado (todas requieren el ticker, ej. AAPL, MSFT, NVDA, TSLA):
- consultar_precio_actual: precio actual de una acción.
- consultar_cierre_anterior: cierre anterior.
- consultar_historico_accion: últimos cierres diarios.
- consultar_indicadores_empresa: P/E, EPS, beta, market cap, dividend yield.
- evaluar_empresa_basico: evaluación simple (estable, moderada o riesgosa).

Herramientas de memoria:
- guardar_dato_usuario: úsala cuando el usuario diga su nombre o un dato personal relevante
  (país, perfil de riesgo, horizonte, empresas que sigue) o te pida que recuerdes algo.
  Usa claves cortas como "nombre", "perfil_riesgo", "empresas_favoritas".
- olvidar_dato_usuario: úsala si el usuario te pide olvidar un dato.
- Nunca guardes contraseñas, claves de API ni datos bancarios. Si te los dan, no los guardes y avísale.

Reglas:
- Si una herramienta devuelve un error (ticker inválido, API caída, límite alcanzado), explícalo en una frase.
- NUNCA des recomendaciones de compra o venta, ni asesoría financiera. Si te piden "qué acciones comprar", explica que no puedes recomendar y ofrece consultar datos de las empresas que le interesen.
- Cuando uses evaluar_empresa_basico, incluye el aviso de que no es asesoría financiera.
- Responde siempre de forma breve y directa.
""".strip()


def _ticker_param(descripcion: str):
    return {
        "type": "object",
        "properties": {"ticker": {"type": "string", "description": descripcion}},
        "required": ["ticker"],
    }


TOOLS = [
    {"type": "function", "function": {
        "name": "consultar_precio_actual",
        "description": "Consulta el precio actual de una acción que cotiza en bolsa.",
        "parameters": _ticker_param("Símbolo bursátil, por ejemplo AAPL")}},
    {"type": "function", "function": {
        "name": "consultar_cierre_anterior",
        "description": "Consulta el precio de cierre anterior de una acción.",
        "parameters": _ticker_param("Símbolo bursátil, por ejemplo MSFT")}},
    {"type": "function", "function": {
        "name": "consultar_historico_accion",
        "description": "Consulta los últimos cierres diarios disponibles de una acción.",
        "parameters": _ticker_param("Símbolo bursátil, por ejemplo NVDA")}},
    {"type": "function", "function": {
        "name": "consultar_indicadores_empresa",
        "description": "Consulta indicadores básicos de una empresa: P/E, EPS, beta, market cap y dividend yield.",
        "parameters": _ticker_param("Símbolo bursátil, por ejemplo TSLA")}},
    {"type": "function", "function": {
        "name": "evaluar_empresa_basico",
        "description": ("Da una evaluación simple de una empresa (estable, moderada o riesgosa) "
                        "basada en indicadores básicos. No es asesoría financiera."),
        "parameters": _ticker_param("Símbolo bursátil, por ejemplo AAPL")}},
    {"type": "function", "function": {
        "name": "guardar_dato_usuario",
        "description": ("Guarda un dato importante del usuario para recordarlo en futuras sesiones "
                        "(nombre, país, perfil de riesgo, preferencias...)."),
        "parameters": {
            "type": "object",
            "properties": {
                "clave": {"type": "string", "description": "Nombre corto del dato, por ejemplo 'nombre'"},
                "valor": {"type": "string", "description": "Valor del dato, por ejemplo 'Rafa'"},
            },
            "required": ["clave", "valor"]}}},
    {"type": "function", "function": {
        "name": "olvidar_dato_usuario",
        "description": "Borra un dato guardado del usuario cuando él pide olvidarlo.",
        "parameters": {
            "type": "object",
            "properties": {"clave": {"type": "string", "description": "Clave del dato a borrar"}},
            "required": ["clave"]}}},
]

# Etiquetas legibles para mostrar en la interfaz qué hizo el agente
TOOL_LABELS = {
    "consultar_precio_actual": "Precio actual",
    "consultar_cierre_anterior": "Cierre anterior",
    "consultar_historico_accion": "Histórico",
    "consultar_indicadores_empresa": "Indicadores",
    "evaluar_empresa_basico": "Evaluación básica",
    "guardar_dato_usuario": "Memoria guardada",
    "olvidar_dato_usuario": "Memoria borrada",
}


def _execute_tool(name: str, args: dict, tools: IntermediateTools, memory) -> dict:
    ticker = args.get("ticker", "")
    if name == "consultar_precio_actual":
        return tools.consultar_precio_actual(ticker=ticker)
    if name == "consultar_cierre_anterior":
        return tools.consultar_cierre_anterior(ticker=ticker)
    if name == "consultar_historico_accion":
        return tools.consultar_historico_accion(ticker=ticker)
    if name == "consultar_indicadores_empresa":
        return tools.consultar_indicadores_empresa(ticker=ticker)
    if name == "evaluar_empresa_basico":
        return tools.evaluar_empresa_basico(ticker=ticker)
    if name == "guardar_dato_usuario":
        if not args.get("clave") or not args.get("valor"):
            return {"error": "Faltan la clave o el valor del dato."}
        memory.save_fact(args["clave"], args["valor"])
        return {"ok": True, "guardado": {args["clave"]: args["valor"]}}
    if name == "olvidar_dato_usuario":
        memory.delete_fact(args.get("clave", ""))
        return {"ok": True}
    print(f"Se intentó llamar a una herramienta desconocida {name}")
    return {"error": f"Herramienta desconocida: {name}"}


def run_agent(client, memory, user_text: str) -> tuple[str, list[str]]:
    """Responde al usuario. Devuelve (texto, herramientas_usadas).
    Guarda la pregunta y la respuesta en la memoria."""
    messages = [{"role": "system", "content": build_system_prompt(memory.facts())}]
    messages.extend(memory.messages())
    messages.append({"role": "user", "content": user_text})

    tools = IntermediateTools()
    used: list[str] = []
    answer = ""

    for _ in range(MAX_TOOL_ROUNDS):
        resp = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS)
        msg = resp.choices[0].message

        if not getattr(msg, "tool_calls", None):
            answer = msg.content or ""
            break

        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [tc.model_dump() for tc in msg.tool_calls],
        })
        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            result = _execute_tool(name, args, tools, memory)
            label = TOOL_LABELS.get(name, name)
            detail = args.get("ticker") or args.get("clave") or ""
            used.append(f"{label} · {detail}".strip(" ·"))
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result, ensure_ascii=False),
            })
    else:
        answer = "No pude completar la consulta. Intenta de nuevo con una pregunta más concreta."

    memory.add("user", user_text)
    memory.add("assistant", answer)
    return answer, used
