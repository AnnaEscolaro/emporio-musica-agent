import pytest

from emporio_agent.policies_rag import chunk_policy_text, extract_pdf_text, search_policies


def test_policy_chunks_keep_sections_apart():
    chunks = chunk_policy_text(extract_pdf_text())
    arrependimento = [chunk for chunk in chunks if "Arrependimento" in chunk]
    horario = [chunk for chunk in chunks if "Horário de Funcionamento" in chunk]

    assert len(chunks) >= 8
    assert arrependimento
    assert horario
    assert all("Horário de Funcionamento" not in chunk for chunk in arrependimento)
    assert any("7" in chunk and "dias" in chunk.lower() for chunk in arrependimento)
    assert all(len(chunk) <= 700 for chunk in chunks)


def test_policy_search_retrieves_portuguese_sections(tmp_path, monkeypatch):
    monkeypatch.setattr("emporio_agent.policies_rag.CHROMA_DIR", tmp_path / "chroma")
    monkeypatch.setattr("emporio_agent.policies_rag.POLICIES_HASH_FILE", tmp_path / "hash")

    try:
        returns = search_policies("posso devolver uma compra online por arrependimento?", top_k=3)
        hours = search_policies("qual o horário de funcionamento no sábado?", top_k=3)
    except Exception as exc:
        pytest.fail(f"Falha ao indexar o manual com embedding multilingual: {exc}")

    return_text = " ".join(hit["excerpt"] for hit in returns).lower()
    hour_text = " ".join(hit["excerpt"] for hit in hours)

    assert "arrependimento" in return_text
    assert "7" in return_text
    assert "13:00" in hour_text or "Sábado" in hour_text
