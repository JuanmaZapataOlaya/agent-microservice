from app.ingest.chunker import chunk_markdown


def test_markdown_is_split_by_characters_and_preserves_paragraphs() -> None:
    text = (
        "# Funcionalidades\n\n"
        "La aplicación permite crear reportes de mascotas perdidas y encontradas. "
        "También permite buscar por ubicación y contactar a otros usuarios.\n\n"
        "## Verificación\n\n"
        "Para contactar al dueño se requieren dos imágenes de evidencia."
    )

    chunks = chunk_markdown(text, size=100, overlap=20)

    assert len(chunks) > 2
    assert all(len(chunk) <= 100 for chunk in chunks)
    assert any("Funcionalidades" in chunk for chunk in chunks)
    assert any("Verificación" in chunk for chunk in chunks)


def test_chunk_overlap_must_be_smaller_than_size() -> None:
    try:
        chunk_markdown("texto", size=40, overlap=40)
    except ValueError as exc:
        assert str(exc) == "chunk overlap must be smaller than chunk size"
    else:
        raise AssertionError("Expected invalid overlap to raise ValueError")
