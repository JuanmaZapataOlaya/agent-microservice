import re


def chunk_markdown(text: str, size: int, overlap: int) -> list[str]:
    words = re.findall(r"\S+", text)
    if overlap >= size:
        raise ValueError("chunk overlap must be smaller than chunk size")
    chunks: list[str] = []
    step = size - overlap
    for start in range(0, len(words), step):
        chunk = " ".join(words[start:start + size])
        if chunk:
            chunks.append(chunk)
        if start + size >= len(words):
            break
    return chunks
