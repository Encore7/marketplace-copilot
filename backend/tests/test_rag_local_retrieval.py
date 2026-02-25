from backend.app.rag import store
from backend.app.schemas.rag import RAGChunk


def test_local_rag_retrieval_filters_by_marketplace(monkeypatch):
    chunks = [
        RAGChunk(
            id="a1",
            text="Amazon listing guideline title rules",
            marketplace="amazon",
            section="listing_guidelines",
            source="amazon/listing_guidelines.md",
        ),
        RAGChunk(
            id="f1",
            text="Flipkart image guideline white background",
            marketplace="flipkart",
            section="image_requirements",
            source="flipkart/image_requirements.md",
        ),
    ]
    monkeypatch.setattr(store, "_load_local_chunks", lambda: chunks)

    result = store._retrieve_local_chunks(
        query="title guideline",
        marketplace="amazon",
        section=None,
        top_k=5,
    )
    assert len(result) == 1
    assert result[0].marketplace == "amazon"
