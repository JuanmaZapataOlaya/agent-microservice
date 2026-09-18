from app.ingest.chunker import chunk_markdown
from app.ingest.markdown_loader import load_markdown
from app.providers.base_llm_provider import LLMProvider
from app.repositories.supabase_repository import SupabaseRepository


class IngestionPipeline:
    def __init__(self, repository: SupabaseRepository, provider: LLMProvider, chunk_size: int, overlap: int) -> None:
        self.repository, self.provider = repository, provider
        self.chunk_size, self.overlap = chunk_size, overlap

    async def ingest(self, filename: str, content: str) -> int:
        text, metadata = load_markdown(filename, content)
        chunks = chunk_markdown(text, self.chunk_size, self.overlap)
        await self.repository.delete_document(filename)
        rows = []
        for index, chunk in enumerate(chunks):
            rows.append({
                "document_name": filename, "chunk_index": index, "chunk_text": chunk,
                "metadata": metadata, "embedding": await self.provider.embed(chunk),
            })
        await self.repository.insert_chunks(rows)
        return len(rows)
