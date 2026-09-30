alter table chat_sessions add column if not exists state jsonb not null default '{}';
