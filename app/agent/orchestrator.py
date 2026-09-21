from uuid import UUID

from app.agent.action_planner import parse_action_plan
from app.agent.deep_agent import DeepAgent
from app.agent.guardrails import GuardrailKind, classify_message, retrieval_query
from app.providers.base_llm_provider import LLMProvider
from app.rag.prompt import build_messages
from app.repositories.supabase_repository import SupabaseRepository


class AgentOrchestrator:
    def __init__(self, repository: SupabaseRepository, provider: LLMProvider, top_k: int, threshold: float) -> None:
        self.repository, self.provider = repository, provider
        self.agent = DeepAgent(provider)
        self.top_k, self.threshold = top_k, threshold

    async def respond(self, session_id: UUID, question: str) -> tuple[str, str | None, dict]:
        guardrail = classify_message(question)
        if guardrail.kind is not GuardrailKind.IN_SCOPE:
            await self.repository.add_message(session_id, "user", question)
            await self.repository.add_message(
                session_id,
                "assistant",
                guardrail.response or "",
            )
            return guardrail.response or "", None, {}

        history = await self.repository.history(session_id)
        embedding = await self.provider.embed(retrieval_query(question))
        chunks = await self.repository.search_chunks(embedding, self.top_k, self.threshold)
        if not chunks and self.threshold > 0:
            chunks = await self.repository.search_chunks(
                embedding, self.top_k, max(self.threshold - 0.15, 0)
            )
        if not chunks:
            chunks = await self.repository.search_chunks(embedding, self.top_k, 0)
        response = await self.agent.run(
            build_messages(history, question, chunks),
            response_format={"type": "json_object"},
        )
        plan = parse_action_plan(response.content)
        await self.repository.add_message(session_id, "user", question)
        await self.repository.add_message(session_id, "assistant", plan.model_dump_json())
        return plan.message, plan.action, plan.payload
