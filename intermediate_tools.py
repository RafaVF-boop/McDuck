#######################
# Agente Financiero   #
# Herramientas        #
#######################

# Importacion para el manejo de sistema
import os
import requests

# URL base de la API de Alpha Vantage
ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"

AVISO_NO_ASESORIA = (
    "Esta evaluación es solo informativa, se basa en indicadores básicos "
    "y NO constituye asesoría financiera ni recomendación de compra o venta."
)


def _a_float(valor):
    try:
        if valor in (None, "None", "-", ""):
            return None
        return float(valor)
    except (TypeError, ValueError):
        return None


def clasificar_riesgo(beta, pe) -> str:
    """Clasificación simple por beta y P/E. Se usa en la herramienta del agente
    y en el panel, para que ambos den siempre el mismo resultado."""
    beta, pe = _a_float(beta), _a_float(pe)
    if beta is None and pe is None:
        return "sin datos suficientes"
    if (beta is not None and beta > 1.5) or (pe is not None and pe > 40):
        return "riesgosa"
    if (beta is not None and beta < 0.8) and (pe is None or pe < 25):
        return "estable"
    return "moderada"


class IntermediateTools:

    def __init__(self):
        pass

    # ---------------------------------------------------------------
    # Funcion auxiliar interna: hace la llamada real a Alpha Vantage
    # y centraliza el manejo de errores (API caida, límite, ticker inválido)
    # ---------------------------------------------------------------
    def _consultar_alpha_vantage(self, params: dict):
        # La clave se lee AQUI, en el momento de la llamada, no al importar
        # el módulo. Si se leyera arriba a nivel de módulo, se ejecutaría
        # antes de que el script principal llame a load_dotenv(), y
        # siempre quedaría vacía sin importar lo que tenga el .env.
        alpha_vantage_api_key = os.environ.get("ALPHA_VANTAGE_API_KEY")
        if not alpha_vantage_api_key:
            return {"error": "No se encontró ALPHA_VANTAGE_API_KEY en el archivo .env."}

        params["apikey"] = alpha_vantage_api_key

        try:
            response = requests.get(ALPHA_VANTAGE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"Error al consultar Alpha Vantage: {e}")
            return {"error": "No se pudo conectar con la API de Alpha Vantage."}

        # Alpha Vantage responde 200 OK incluso cuando hay un error,
        # así que hay que revisar el contenido del JSON.
        if "Note" in data or "Information" in data:
            return {"error": "Se alcanzó el límite de peticiones de Alpha Vantage. Intenta de nuevo en un momento."}
        if "Error Message" in data:
            return {"error": "El ticker no existe o no es válido."}
        if not data:
            return {"error": "Alpha Vantage no devolvió datos."}

        return data

    # ---------------------------------------------------------------
    # 1. Precio actual
    # ---------------------------------------------------------------
    def consultar_precio_actual(self, ticker: str):
        print(f"Herramienta consultar_precio_actual llamada con ticker: {ticker}")

        if not ticker:
            return {"error": "Se requiere el ticker de la empresa."}

        data = self._consultar_alpha_vantage({
            "function": "GLOBAL_QUOTE",
            "symbol": ticker.upper()
        })
        if "error" in data:
            return data

        quote = data.get("Global Quote", {})
        if not quote or not quote.get("05. price"):
            return {"error": f"No se encontraron datos para el ticker: {ticker}"}

        return {
            "ticker": ticker.upper(),
            "precio_actual": quote.get("05. price"),
            "variacion": quote.get("09. change"),
            "variacion_porcentual": quote.get("10. change percent"),
            "fecha": quote.get("07. latest trading day")
        }

    # ---------------------------------------------------------------
    # 2. Cierre anterior
    # ---------------------------------------------------------------
    def consultar_cierre_anterior(self, ticker: str):
        print(f"Herramienta consultar_cierre_anterior llamada con ticker: {ticker}")

        if not ticker:
            return {"error": "Se requiere el ticker de la empresa."}

        data = self._consultar_alpha_vantage({
            "function": "GLOBAL_QUOTE",
            "symbol": ticker.upper()
        })
        if "error" in data:
            return data

        quote = data.get("Global Quote", {})
        if not quote or not quote.get("08. previous close"):
            return {"error": f"No se encontraron datos para el ticker: {ticker}"}

        return {
            "ticker": ticker.upper(),
            "cierre_anterior": quote.get("08. previous close"),
            "fecha": quote.get("07. latest trading day")
        }

    # ---------------------------------------------------------------
    # 3. Historico de cierres diarios
    # ---------------------------------------------------------------
    def consultar_historico_accion(self, ticker: str, dias: int = 5):
        print(f"Herramienta consultar_historico_accion llamada con ticker: {ticker}")

        if not ticker:
            return {"error": "Se requiere el ticker de la empresa."}

        data = self._consultar_alpha_vantage({
            "function": "TIME_SERIES_DAILY",
            "symbol": ticker.upper(),
            "outputsize": "compact"
        })
        if "error" in data:
            return data

        serie = data.get("Time Series (Daily)", {})
        if not serie:
            return {"error": f"No se encontraron datos históricos para el ticker: {ticker}"}

        fechas_ordenadas = sorted(serie.keys(), reverse=True)[:dias]
        historico = [
            {"fecha": fecha, "cierre": serie[fecha]["4. close"]}
            for fecha in fechas_ordenadas
        ]

        return {
            "ticker": ticker.upper(),
            "historico": historico
        }

    # ---------------------------------------------------------------
    # 4. Indicadores basicos de la empresa
    # ---------------------------------------------------------------
    def consultar_indicadores_empresa(self, ticker: str):
        print(f"Herramienta consultar_indicadores_empresa llamada con ticker: {ticker}")

        if not ticker:
            return {"error": "Se requiere el ticker de la empresa."}

        data = self._consultar_alpha_vantage({
            "function": "OVERVIEW",
            "symbol": ticker.upper()
        })
        if "error" in data:
            return data

        if not data.get("Symbol"):
            return {"error": f"No se encontraron indicadores para el ticker: {ticker}"}

        return {
            "ticker": data.get("Symbol"),
            "nombre": data.get("Name"),
            "pe_ratio": data.get("PERatio"),
            "eps": data.get("EPS"),
            "beta": data.get("Beta"),
            "market_cap": data.get("MarketCapitalization"),
            "dividend_yield": data.get("DividendYield"),
            "sector": data.get("Sector")
        }

    # ---------------------------------------------------------------
    # 5. Evaluacion basica (NO es asesoria financiera)
    # ---------------------------------------------------------------
    def evaluar_empresa_basico(self, ticker: str):
        print(f"Herramienta evaluar_empresa_basico llamada con ticker: {ticker}")

        if not ticker:
            return {"error": "Se requiere el ticker de la empresa."}

        indicadores = self.consultar_indicadores_empresa(ticker)
        if "error" in indicadores:
            return indicadores

        return {
            "ticker": indicadores.get("ticker"),
            "beta": indicadores.get("beta"),
            "pe_ratio": indicadores.get("pe_ratio"),
            "evaluacion": clasificar_riesgo(indicadores.get("beta"), indicadores.get("pe_ratio")),
            "aviso": AVISO_NO_ASESORIA
        }
