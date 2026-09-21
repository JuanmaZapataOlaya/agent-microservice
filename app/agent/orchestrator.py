import logging
from uuid import UUID

from app.agent.action_planner import parse_action_plan
from app.agent.deep_agent import DeepAgent
from app.agent.guardrails import (
    GuardrailKind,
    classify_intent,
    classify_message,
    retrieval_query,
)
from app.models.schemas import ActionPlan
from app.providers.base_llm_provider import LLMProvider
from app.rag.prompt import build_messages
from app.repositories.supabase_repository import SupabaseRepository

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    def __init__(
        self,
        repository: SupabaseRepository,
        provider: LLMProvider,
        top_k: int,
        threshold: float,
        guardrail_model: str,
    ) -> None:
        self.repository, self.provider = repository, provider
        self.agent = DeepAgent(provider)
        self.top_k, self.threshold = top_k, threshold
        self.guardrail_model = guardrail_model

    async def respond(self, session_id: UUID, question: str) -> tuple[str, str | None, dict]:
        guardrail = classify_message(question)
        if guardrail.kind is GuardrailKind.GREETING:
            await self.repository.add_message(session_id, "user", question)
            await self.repository.add_message(
                session_id,
                "assistant",
                guardrail.response or "",
            )
            return guardrail.response or "", None, {}

        history = await self.repository.history(session_id)
        cleaned_question = guardrail.cleaned_message
        if not cleaned_question:
            cleaned_question = question
        if guardrail.kind is None:
            guardrail = await classify_intent(
                self.provider,
                cleaned_question,
                self.guardrail_model,
                history,
            )
        if guardrail.kind is not GuardrailKind.IN_SCOPE:
            await self.repository.add_message(session_id, "user", question)
            await self.repository.add_message(
                session_id,
                "assistant",
                guardrail.response or "",
            )
            return guardrail.response or "", None, {}

        embedding = await self.provider.embed(retrieval_query(cleaned_question))
        chunks = await self.repository.search_chunks(embedding, self.top_k, self.threshold)
        if not chunks and self.threshold > 0:
            chunks = await self.repository.search_chunks(
                embedding, self.top_k, max(self.threshold - 0.15, 0)
            )
        if not chunks:
            chunks = await self.repository.search_chunks(embedding, self.top_k, 0)
        messages = build_messages(history, cleaned_question, chunks)
        plan = await self._parse_agent_plan(messages)
        await self.repository.add_message(session_id, "user", question)
        await self.repository.add_message(session_id, "assistant", plan.model_dump_json())
        return plan.message, plan.action, plan.payload

    async def _parse_agent_plan(
        self,
        messages: list[dict[str, str]],
    ) -> ActionPlan:
        response = await self.agent.run(
            messages,
            response_format={"type": "json_object"},
        )
        try:
            return parse_action_plan(response.content)
        except ValueError as first_error:
            logger.warning("agent_invalid_action_plan_retry")
            repair_messages = [
                *messages,
                {
                    "role": "user",
                    "content": (
                        "La respuesta anterior no cumplió el contrato. "
                        "Responde únicamente con un objeto JSON válido con exactamente "
                        'message, action y payload. Para esta consulta usa action null '
                        "si faltan datos; no agregues texto fuera del JSON."
                    ),
                },
            ]
            retry = await self.agent.run(
                repair_messages,
                response_format={"type": "json_object"},
            )
            try:
                return parse_action_plan(retry.content)
            except ValueError:
                logger.error("agent_invalid_action_plan_fallback", exc_info=first_error)
                return ActionPlan(
                    message=(
                        "No pude procesar la respuesta en este momento. "
                        "Puedes intentar de nuevo con los datos de tu mascota."
                    ),
                    action=None,
                    payload={},
                )
