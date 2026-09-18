from datetime import datetime, timedelta, timezone
from uuid import UUID
from app.repositories.supabase_repository import SupabaseRepository


class SessionService:
    def __init__(self, repository: SupabaseRepository, ttl_minutes: int) -> None:
        self.repository, self.ttl_minutes = repository, ttl_minutes

    async def start(self, user_id: str) -> dict:
        expires = datetime.now(timezone.utc) + timedelta(minutes=self.ttl_minutes)
        return await self.repository.create_session(user_id, expires)

    async def require_active(self, session_id: UUID, user_id: str | None = None) -> dict:
        session = await self.repository.get_active_session(session_id, user_id)
        if not session:
            raise ValueError("Session is missing or expired")
        return session
