"""A provider failure must not become a cached, successful empty extraction."""
import hashlib

import pytest

from app.storage.extraction_cache import ExtractionCache
from app.storage.neo4j_storage import Neo4jStorage
from app.storage.ner_extractor import NERExtractor

ONTOLOGY = {"entity_types": [{"name": "Party"}], "edge_types": []}


class FailingLLM:
    def __init__(self, fail_when=lambda text: True):
        self.fail_when = fail_when
        self.calls = 0
        self.prompts = []

    def chat_json(self, messages, **kwargs):
        self.calls += 1
        self.prompts.append(messages[-1]["content"])
        if self.fail_when(messages[-1]["content"]):
            raise RuntimeError("401 unauthorized")
        return {"entities": [], "relations": []}


def storage_with(llm, tmp_path):
    storage = Neo4jStorage.__new__(Neo4jStorage)
    storage._ner = NERExtractor(llm_client=llm, max_retries=0)
    storage._extraction_cache = ExtractionCache(tmp_path)
    storage._assert_embedding_compatible = lambda graph_id: None
    storage.get_ontology = lambda graph_id: ONTOLOGY
    storage._write_extractions_batch = (
        lambda graph_id, chunks, extractions, profile=None:
        [hashlib.sha256(text.encode()).hexdigest() for text in chunks]
    )
    return storage


def test_extractor_marks_a_provider_failure():
    result = NERExtractor(llm_client=FailingLLM(), max_retries=0).extract("Alpha met Beta.", ONTOLOGY)

    assert result == {"entities": [], "relations": [], "failed": True}


def test_total_extraction_failure_stops_the_build_and_is_not_cached(tmp_path):
    llm = FailingLLM()
    storage = storage_with(llm, tmp_path)
    context = {"file_hash": "file-1"}

    with pytest.raises(RuntimeError, match="Entity extraction failed"):
        storage.add_text_batch("graph-1", ["Alpha met Beta."], cache_context=context)

    calls = llm.calls
    with pytest.raises(RuntimeError):
        storage.add_text_batch("graph-1", ["Alpha met Beta."], cache_context=context)
    assert llm.calls > calls


def test_single_chunk_failure_is_not_written_as_processed(tmp_path):
    storage = storage_with(FailingLLM(), tmp_path)
    storage._write_extraction = lambda *args: pytest.fail("a failed extraction must not be written")

    with pytest.raises(RuntimeError, match="Entity extraction failed"):
        storage.add_text("graph-1", "Alpha met Beta.")


def test_partial_failure_is_retried_on_rebuild_while_successes_stay_cached(tmp_path):
    llm = FailingLLM(fail_when=lambda text: "Gamma" in text)
    storage = storage_with(llm, tmp_path)
    context = {"file_hash": "file-2"}
    chunks = ["Alpha met Beta.", "Gamma met Delta."]

    storage._write_extractions_batch = lambda *args, **kwargs: pytest.fail("a build with a failed chunk must not be written")
    with pytest.raises(RuntimeError, match="failed for 1 of 2 chunks"):
        storage.add_text_batch("graph-1", chunks, cache_context=context)

    storage._write_extractions_batch = lambda graph_id, chunks, extractions, profile=None: list(chunks)
    llm.fail_when = lambda text: False
    llm.prompts = []
    assert len(storage.add_text_batch("graph-1", chunks, cache_context=context)) == 2
    # Only the chunk that failed is asked again.
    assert llm.prompts and all("Gamma" in prompt and "Alpha" not in prompt for prompt in llm.prompts)
