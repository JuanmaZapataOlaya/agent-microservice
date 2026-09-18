from pathlib import PurePath


def load_markdown(filename: str, content: str) -> tuple[str, dict]:
    if PurePath(filename).suffix.lower() not in {".md", ".markdown"}:
        raise ValueError("Only Markdown documents are accepted")
    return content.replace("\x00", ""), {"document_name": filename}
