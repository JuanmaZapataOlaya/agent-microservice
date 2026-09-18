create extension if not exists vector;
create extension if not exists pg_cron;

create table if not exists knowledge_chunks (
  id uuid primary key default gen_random_uuid(), document_name text not null,
  chunk_index integer not null, chunk_text text not null, metadata jsonb not null default '{}',
  embedding vector(768) not null, created_at timestamptz not null default now(),
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

create or replace function check_rate_limit(subject_key text, max_requests integer default 30)
returns boolean language plpgsql security definer as $$
declare current_window timestamptz := date_trunc('minute', now());
declare new_count integer;
begin
  insert into rate_limit_windows(subject, window_start, request_count)
  values (subject_key, current_window, 1)
  on conflict (subject, window_start) do update
    set request_count = rate_limit_windows.request_count + 1
    returning request_count into new_count;
  delete from rate_limit_windows where window_start < current_window - interval '5 minutes';
  return new_count <= max_requests;
end; $$;
grant execute on function check_rate_limit(text, integer) to authenticated;

create or replace function match_knowledge_chunks(
  query_embedding vector(768), match_count integer, similarity_threshold float
) returns table (id uuid, document_name text, chunk_index integer, chunk_text text, metadata jsonb, similarity float)
language sql stable as $$
  select id, document_name, chunk_index, chunk_text, metadata,
    1 - (embedding <=> query_embedding) as similarity
  from knowledge_chunks
  where 1 - (embedding <=> query_embedding) >= similarity_threshold
  order by embedding <=> query_embedding limit match_count;
$$;

create or replace function cleanup_expired_sessions() returns void
language sql security definer as $$ delete from chat_sessions where expires_at <= now(); $$;
select cron.schedule('cleanup-expired-chat-sessions', '*/15 * * * *', $$select cleanup_expired_sessions();$$);
