create extension if not exists vector;
create extension if not exists pg_cron;

create table if not exists knowledge_chunks (
  id uuid primary key default gen_random_uuid(), document_name text not null,
  chunk_index integer not null, chunk_text text not null, metadata jsonb not null default '{}',
  embedding extensions.vector(1536) not null, created_at timestamptz not null default now(),
  unique (document_name, chunk_index)
);
create index if not exists knowledge_chunks_embedding_idx
  on knowledge_chunks using hnsw (embedding vector_cosine_ops);

create table if not exists chat_sessions (
  id uuid primary key default gen_random_uuid(), user_id text not null,
  created_at timestamptz not null default now(), expires_at timestamptz not null
);
create index if not exists chat_sessions_expiry_idx on chat_sessions(expires_at);

create table if not exists chat_messages (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references chat_sessions(id) on delete cascade,
  role text not null check (role in ('user', 'assistant')), content text not null,
  created_at timestamptz not null default now()
);
create index if not exists chat_messages_session_idx on chat_messages(session_id, created_at);

create table if not exists rate_limit_windows (
  subject text not null, window_start timestamptz not null, request_count integer not null default 0,
  primary key (subject, window_start)
);

-- These tables are accessed by the FastAPI service with the service_role key.
-- Enable RLS so anon/authenticated clients cannot read or mutate backend data.
-- No client policies are intentional: access is exclusively through the API.
alter table knowledge_chunks enable row level security;
alter table chat_sessions enable row level security;
alter table chat_messages enable row level security;
alter table rate_limit_windows enable row level security;

grant all on table knowledge_chunks, chat_sessions, chat_messages, rate_limit_windows to service_role;

create or replace function check_rate_limit(subject_key text, max_requests integer default 30)
returns boolean
language plpgsql
security definer
set search_path = public
as $$
declare current_window timestamptz := date_trunc('minute', now());
declare new_count integer;
begin
  insert into public.rate_limit_windows(subject, window_start, request_count)
  values (subject_key, current_window, 1)
  on conflict (subject, window_start) do update
    set request_count = public.rate_limit_windows.request_count + 1
    returning request_count into new_count;
  delete from public.rate_limit_windows
  where window_start < current_window - interval '5 minutes';
  return new_count <= max_requests;
end; $$;
revoke execute on function check_rate_limit(text, integer) from public;
grant execute on function check_rate_limit(text, integer) to authenticated;
grant execute on function check_rate_limit(text, integer) to service_role;

create or replace function match_knowledge_chunks(
  query_embedding extensions.vector(1536), match_count integer, similarity_threshold float
)
returns table (id uuid, document_name text, chunk_index integer, chunk_text text, metadata jsonb, similarity float)
language sql
stable
security definer
set search_path = public, extensions
as $$
  select kc.id, kc.document_name, kc.chunk_index, kc.chunk_text, kc.metadata,
    1 - (kc.embedding <=> query_embedding) as similarity
  from public.knowledge_chunks kc
  where 1 - (kc.embedding <=> query_embedding) >= similarity_threshold
  order by kc.embedding <=> query_embedding limit match_count;
$$;
revoke execute on function match_knowledge_chunks(extensions.vector(1536), integer, double precision) from public;
grant execute on function match_knowledge_chunks(extensions.vector(1536), integer, double precision) to service_role;

create or replace function cleanup_expired_sessions()
returns void
language sql
security definer
set search_path = public
as $$
  delete from public.chat_sessions where expires_at <= now();
$$;
revoke execute on function cleanup_expired_sessions() from public;
grant execute on function cleanup_expired_sessions() to service_role;

do $$
begin
  if not exists (
    select 1 from cron.job
    where jobname = 'cleanup-expired-chat-sessions'
  ) then
    perform cron.schedule(
      'cleanup-expired-chat-sessions',
      '*/15 * * * *',
      'select public.cleanup_expired_sessions();'
    );
  end if;
end;
$$;
