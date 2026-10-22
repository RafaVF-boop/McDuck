"""
Memoria de McDuck.

Dos implementaciones con la MISMA interfaz:
  - SupabaseMemory: guarda en Supabase, sobrevive a cerrar la app.
  - LocalMemory:    guarda en RAM, se pierde al cerrar. Solo es el respaldo
                    cuando Supabase no está configurado.

Hay dos tipos de recuerdo:
  - mensajes: la conversación (tabla `messages`).
  - datos:    hechos importantes del usuario, como su nombre (tabla `user_facts`).

Interfaz:
  messages()            -> últimos N mensajes para dar contexto al modelo
  history(limit)        -> historial para mostrar en pantalla
  add(role, content)    -> guarda un mensaje
  facts()               -> {clave: valor}
  save_fact(k, v) / delete_fact(k)
  clear_history()
"""

import re

MEMORY_MAX_MESSAGES = 10   # mensajes que se le pasan al modelo como contexto


def clean_key(key: str) -> str:
    """Normaliza la clave de un dato: 'Mi Nombre!' -> 'mi_nombre'."""
    key = re.sub(r"[^a-z0-9_áéíóúñ ]", "", str(key).lower().strip())
    return re.sub(r"\s+", "_", key)[:60]


class LocalMemory:
    persistent = False

    def __init__(self, user_id: str, max_messages: int = MEMORY_MAX_MESSAGES, store: dict | None = None):
        self.user_id = user_id
        self.max_messages = max_messages
        # `store` permite que Streamlit conserve los datos entre recargas
        self._store = store if store is not None else {"messages": [], "facts": {}}

    def messages(self) -> list[dict]:
        return list(self._store["messages"][-self.max_messages:])

    def history(self, limit: int = 100) -> list[dict]:
        return list(self._store["messages"][-limit:])

    def add(self, role: str, content: str) -> None:
        self._store["messages"].append({"role": role, "content": content})

    def facts(self) -> dict:
        return dict(self._store["facts"])

    def save_fact(self, key: str, value: str) -> None:
        key = clean_key(key)
        if key:
            self._store["facts"][key] = str(value)[:500]

    def delete_fact(self, key: str) -> None:
        self._store["facts"].pop(clean_key(key), None)

    def clear_history(self) -> None:
        self._store["messages"].clear()


class SupabaseMemory:
    persistent = True

    def __init__(self, client, user_id: str, max_messages: int = MEMORY_MAX_MESSAGES):
        self.db = client
        self.user_id = user_id
        self.max_messages = max_messages

    def _last(self, n: int) -> list[dict]:
        res = (self.db.table("messages")
               .select("role, content")
               .eq("user_id", self.user_id)
               .order("created_at", desc=True)
               .limit(n)
               .execute())
        return list(reversed(res.data or []))   # de más antiguo a más nuevo

    def messages(self) -> list[dict]:
        return self._last(self.max_messages)

    def history(self, limit: int = 100) -> list[dict]:
        return self._last(limit)

    def add(self, role: str, content: str) -> None:
        self.db.table("messages").insert(
            {"user_id": self.user_id, "role": role, "content": content}
        ).execute()

    def facts(self) -> dict:
        res = (self.db.table("user_facts")
               .select("key, value")
               .eq("user_id", self.user_id)
               .order("key")
               .execute())
        return {r["key"]: r["value"] for r in (res.data or [])}

    def save_fact(self, key: str, value: str) -> None:
        key = clean_key(key)
        if not key:
            return
        self.db.table("user_facts").upsert(
            {"user_id": self.user_id, "key": key, "value": str(value)[:500]},
            on_conflict="user_id,key",
        ).execute()

    def delete_fact(self, key: str) -> None:
        (self.db.table("user_facts").delete()
         .eq("user_id", self.user_id).eq("key", clean_key(key)).execute())

    def clear_history(self) -> None:
        self.db.table("messages").delete().eq("user_id", self.user_id).execute()


def make_supabase_client(url: str | None, key: str | None):
    """Devuelve el cliente de Supabase, o None si falta configuración."""
    if not url or not key:
        return None
    from supabase import create_client
    return create_client(url, key)
