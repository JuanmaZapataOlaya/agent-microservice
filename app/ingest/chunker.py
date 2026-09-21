from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_markdown(text: str, size: int, overlap: int) -> list[str]:
    if size < 1:
        raise ValueError("chunk size must be positive")
    if overlap >= size:
        raise ValueError("chunk overlap must be smaller than chunk size")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )
    return splitter.split_text(text)
