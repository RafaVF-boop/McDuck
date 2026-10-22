-- Pega este script completo en Supabase > SQL Editor > New query > Run.
-- Es seguro ejecutarlo más de una vez.

-- 1) Conversación: un registro por mensaje
create table if not exists public.messages (
  id         bigint generated always as identity primary key,
  user_id    text        not null,
  role       text        not null check (role in ('user', 'assistant')),
  content    text        not null,
  created_at timestamptz not null default now()
);
create index if not exists messages_user_created_idx
  on public.messages (user_id, created_at desc);

-- 2) Datos importantes del usuario (nombre, perfil, preferencias...)
create table if not exists public.user_facts (
  user_id    text        not null,
  key        text        not null,
  value      text        not null,
  updated_at timestamptz not null default now(),
  primary key (user_id, key)
);

-- 3) Seguridad: activar RLS y NO crear políticas.
--    Así nadie puede leer ni escribir con la clave pública (anon).
--    La app usa la clave `service_role`, que está en el servidor de
--    Streamlit (secrets) y se salta RLS. Nunca la pongas en GitHub.
alter table public.messages   enable row level security;
alter table public.user_facts enable row level security;
