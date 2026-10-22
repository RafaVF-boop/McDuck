# McDuck · asistente de bolsa

App de Streamlit con un agente financiero (Groq), datos de mercado, gráficos y memoria permanente en Supabase.
Proyecto educativo: nada de lo que muestra es asesoría financiera.

## Qué hace cada archivo

| Archivo | Para qué sirve |
|---|---|
| `app.py` | La interfaz de Streamlit: banner, panel de mercado, chat y memoria |
| `agent.py` | El agente: prompt, herramientas y bucle de llamadas a Groq |
| `intermediate_tools.py` | Las 5 herramientas de bolsa (Alpha Vantage) |
| `market_data.py` | Datos del panel y del banner (Yahoo Finance, con respaldo) |
| `memory.py` | Memoria en Supabase (y memoria temporal de respaldo) |
| `ui.py` | Estilos, banner y gráficos |
| `supabase_schema.sql` | Crea las tablas en Supabase |
| `.streamlit/config.toml` | Tema de colores |

## 1. Probar en tu computador

```powershell
# En la carpeta del proyecto
python -m pip install -r requirements.txt
copy .env.example .env        # y completa tus claves en .env
python -m streamlit run app.py
```

Se abre en http://localhost:8501. Sin claves de Supabase la app funciona igual, pero la memoria se pierde al cerrarla.

## 2. Conectar Supabase (memoria permanente)

1. Entra a https://supabase.com, crea una cuenta y un proyecto nuevo (plan gratuito).
2. Abre **SQL Editor > New query**, pega todo `supabase_schema.sql` y pulsa **Run**.
3. Abre **Project Settings > API** y copia dos valores:
   - **Project URL** → `SUPABASE_URL`
   - **service_role** key (en "Project API keys") → `SUPABASE_KEY`
4. Ponlos en tu `.env`.

La clave `service_role` salta las reglas de seguridad de la base de datos. Por eso solo debe vivir en tu `.env` y en los Secrets de Streamlit, nunca en el código ni en GitHub. Las tablas tienen RLS activado y sin políticas, así que la clave pública no puede leer nada.

Para comprobar que funciona: dile a McDuck "me llamo Rafa", cierra la app, ábrela otra vez y pregunta "¿cómo me llamo?". También verás el dato en **Table Editor > user_facts**.

## 3. Subir a GitHub

```powershell
git init
git add .
git status          # comprueba que .env NO aparece en la lista
git commit -m "McDuck: asistente de bolsa"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/mcduck.git
git push -u origin main
```

Crea antes el repositorio vacío en github.com (botón **New**). Si `.env` aparece en `git status`, detente: revisa que el archivo `.gitignore` esté en la carpeta.

## 4. Publicar en Streamlit Community Cloud (gratis)

1. Entra a https://share.streamlit.io con tu cuenta de GitHub y pulsa **Create app**.
2. Elige tu repositorio, la rama `main` y el archivo `app.py`.
3. En **Advanced settings > Secrets** pega esto con tus claves reales:

```toml
GROQ_API_KEY = "..."
ALPHA_VANTAGE_API_KEY = "..."
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_KEY = "..."
APP_PASSWORD = "una_contraseña"
```

4. Pulsa **Deploy**.

Pon `APP_PASSWORD`: si no, cualquiera con el enlace gasta tu cuota de Groq y escribe en tu base de datos.

## Cómo funciona la memoria

- Cada **perfil** (campo "Tu perfil" a la izquierda) tiene su propia memoria. Usa siempre el mismo nombre de perfil; queda guardado en la URL (`?u=rafa`), así que puedes guardarla como marcador.
- McDuck guarda dos cosas: la conversación (tabla `messages`) y datos importantes como tu nombre (tabla `user_facts`).
- Los datos se inyectan en el prompt en cada conversación. McDuck los guarda solo cuando se lo dices ("me llamo Rafa", "recuerda que mi perfil es conservador"). Puedes verlos, agregarlos y borrarlos en la pestaña **Memoria**.
- El perfil no es un inicio de sesión: quien conozca el nombre de otro perfil puede escribirlo. Para varios usuarios reales usa Supabase Auth.

## Datos de mercado: límites que conviene conocer

- **Alpha Vantage gratis**: unas 25 consultas al día. Lo usan las herramientas del agente y la fila de indicadores del panel (se guarda en caché 6 horas por empresa).
- **Banner, índices y gráficos**: usan Yahoo Finance (`yfinance`), que no necesita clave pero no es una API oficial y a veces limita las consultas desde servidores en la nube. Se guarda en caché 5 minutos.
- Si Yahoo falla, la app avisa y muestra **datos de demostración** marcados como tales. Nunca los presenta como cotizaciones reales.

## Cambiar cosas

- Acciones del banner: `POPULARES` en `market_data.py`.
- Dirección del banner: en `ui.py`, el `@keyframes ticker-ltr`. Para que vaya de derecha a izquierda, cambia `from`/`to` entre sí.
- Colores: `ui.py` (arriba) y `.streamlit/config.toml`.
- Modelo de Groq: `MODEL` en `agent.py`.

## Preguntas de ejemplo

- ¿Cuál es el precio actual de AAPL?
- ¿Cuánto cerró ayer MSFT?
- Dame los últimos cierres de NVDA.
- ¿Qué indicadores básicos tiene TSLA?
- ¿Apple parece una empresa estable o riesgosa?
- Me llamo Rafa y mi perfil de riesgo es conservador. Recuérdalo.
- ¿Cómo me llamo?
