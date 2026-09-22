"""Utilities for compressing retrieved RAG context with LLMLingua-2."""

from __future__ import annotations

from typing import Any, TypedDict


class CompressionResult(TypedDict):
    """Metrics returned after compressing a retrieved context."""

    compressed_context: str
    original_tokens: int
    compressed_tokens: int
    savings_ratio: float


class ContextCompressor:
    """Compress retrieved chunks while preserving information relevant to a query.

    Args:
        model_name: Hugging Face model used by LLMLingua-2.
        device: Device on which to load the model. If omitted, CUDA is selected
            when available and CPU otherwise.
        use_fp16: Whether to use half precision on CUDA.

    Raises:
        RuntimeError: If LLMLingua or the compression model cannot be loaded.
    """

    DEFAULT_MODEL_NAME = "microsoft/llmlingua-2-bert-base-multilingual-cased"

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        device: str | None = None,
        use_fp16: bool = True,
    ) -> None:
        self.model_name = model_name
        self.use_fp16 = use_fp16

        try:
            import torch
            from llmlingua import PromptCompressor

            self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
            if self.device not in {"cpu", "cuda"} and not self.device.startswith(
                ("cuda:", "cpu:")
            ):
                raise ValueError("device debe ser 'cuda', 'cuda:N' o 'cpu'.")

            torch_dtype = (
                torch.float16
                if use_fp16 and self.device.startswith("cuda")
                else torch.float32
            )
            self._compressor = PromptCompressor(
                model_name=model_name,
                device_map=self.device,
                model_config={"torch_dtype": torch_dtype},
                use_llmlingua2=True,
            )
        except Exception as exc:
            raise RuntimeError(
                f"No se pudo cargar el modelo de compresión '{model_name}'."
            ) from exc

    def compress_chunks(
        self, chunks: list[str], query: str, rate: float = 0.4
    ) -> CompressionResult:
        """Compress retrieved chunks according to their relevance to a query.

        Args:
            chunks: Text fragments retrieved by the RAG pipeline.
            query: User question used to prioritize relevant information.
            rate: Target fraction of context tokens to retain, from 0 (exclusive)
                to 1 (inclusive). The resulting fraction can vary slightly
                because token boundaries differ between models.

        Returns:
            A dictionary containing the compressed context and token metrics.

        Raises:
            ValueError: If the input chunks, query, or retention rate is invalid.
            RuntimeError: If LLMLingua fails to compress the context.
        """
        if not chunks:
            raise ValueError("La lista de chunks no puede estar vacía.")
        if any(not isinstance(chunk, str) for chunk in chunks):
            raise ValueError("Todos los chunks deben ser cadenas de texto.")
        if not any(chunk.strip() for chunk in chunks):
            raise ValueError("La lista de chunks no puede estar vacía.")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("La consulta no puede estar vacía.")
        if not 0 < rate <= 1:
            raise ValueError("rate debe ser mayor que 0 y menor o igual que 1.")
        context_chunks = [chunk for chunk in chunks if chunk.strip()]
        try:
            result: Any = self._compressor.compress_prompt(
                context_chunks,
                question=query,
                rate=rate,
                force_tokens=["\n"],
            )
            compressed_context = result["compressed_prompt"]
            original_tokens = int(result["origin_tokens"])
            compressed_tokens = int(result["compressed_tokens"])
        except Exception as exc:
            raise RuntimeError("No se pudo comprimir el contexto recuperado.") from exc

        if original_tokens <= 0:
            savings_ratio = 0.0
        else:
            savings_ratio = 1 - (compressed_tokens / original_tokens)

        return {
            "compressed_context": compressed_context,
            "original_tokens": original_tokens,
            "compressed_tokens": compressed_tokens,
            "savings_ratio": savings_ratio,
        }


if __name__ == "__main__":
    compressor = ContextCompressor()
    chunks = [
        "Las mascotas perdidas pueden registrarse indicando especie, raza, color y descripción.",
        "La aplicación permite buscar perros y gatos por características físicas y ubicación.",
        "Para reportar una mascota encontrada, incluye una descripción detallada y datos de contacto.",
    ]
    question = "¿Cómo puedo buscar un perro perdido?"
    metrics = compressor.compress_chunks(chunks, question)

    print("Contexto comprimido:")
    print(metrics["compressed_context"])
    print(f"\nTokens originales: {metrics['original_tokens']}")
    print(f"Tokens comprimidos: {metrics['compressed_tokens']}")
    print(f"Ahorro de tokens: {metrics['savings_ratio']:.2%}")
