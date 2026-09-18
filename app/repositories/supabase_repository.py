from datetime import datetime, timezone
from typing import Any
from uuid import UUID
from supabase import AsyncClient, acreate_client


class SupabaseRepository:
    def __init__(self, client: AsyncClient) -> None:
        self.client = client

    async def create_session(self, user_id: str, expires_at: datetime) -> dict[str, Any]:
        result = await self.client.table("chat_sessions").insert(
            {"user_id": user_id, "expires_at": expires_at.isoformat()}
        ).execute()
        return result.data[0]

    async def get_active_session(self, session_id: UUID, user_id: str | None = None) -> dict[str, Any] | None:
        query = self.client.table("chat_sessions").select("*").eq("id", str(session_id)).gt(
            "expires_at", datetime.now(timezone.utc).isoformat()
        )
        if user_id:
            query = query.eq("user_id", user_id)
        result = await query.maybe_single().execute()
        return result.data

    async def end_session(self, session_id: UUID) -> None:
        await self.client.table("chat_sessions").delete().eq("id", str(session_id)).execute()

    async def history(self, session_id: UUID, limit: int = 20) -> list[dict[str, Any]]:
        result = await self.client.table("chat_messages").select("role,content").eq(
            "session_id", str(session_id)
        ).order("created_at", desc=False).limit(limit).execute()
        return result.data

    async def add_message(self, session_id: UUID, role: str, content: str) -> None:
        await self.client.table("chat_messages").insert(
            {"session_id": str(session_id), "role": role, "content": content}
        ).execute()

    async def search_chunks(self, embedding: list[float], top_k: int, threshold: float) -> list[dict[str, Any]]:
        result = await self.client.rpc("match_knowledge_chunks", {
            "query_embedding": embedding, "match_count": top_k, "similarity_threshold": threshold
        }).execute()
        return result.data

    async def insert_chunks(self, rows: list[dict[str, Any]]) -> None:
        if rows:
            await self.client.table("knowledge_chunks").insert(rows).execute()

    async def delete_document(self, document_name: str) -> None:
        await self.client.table("knowledge_chunks").delete().eq("document_name", document_name).execute()
