import asyncio
import pytest
import sys
sys.path.insert(0, "backend")

from services.graph_store import GraphStore

TEST_NS = "test-graphstore-ns"

@pytest.fixture(autouse=True)
def clean_namespace():
    store = GraphStore()
    store.clear_namespace(TEST_NS)
    yield
    store.clear_namespace(TEST_NS)
    store.close()


def test_upsert_entities_returns_count():
    store = GraphStore()
    entities = [
        {"name": "Python", "type": "Language", "description": "Programming language"},
        {"name": "FastAPI", "type": "Framework", "description": "Python web framework"},
    ]
    relations = [{"from": "FastAPI", "to": "Python", "type": "BUILT_WITH"}]
    count = store.upsert_entities(entities, relations, TEST_NS)
    assert count == 2


def test_upsert_is_idempotent():
    store = GraphStore()
    entities = [{"name": "Python", "type": "Language", "description": "Lang"}]
    store.upsert_entities(entities, [], TEST_NS)
    store.upsert_entities(entities, [], TEST_NS)
    related = store.query_related(["Python"], TEST_NS)
    assert sum(1 for e in related if e["name"] == "Python") == 1


def test_query_related_finds_connected_entities():
    store = GraphStore()
    entities = [
        {"name": "Python", "type": "Language", "description": "Lang"},
        {"name": "FastAPI", "type": "Framework", "description": "Framework"},
        {"name": "Pydantic", "type": "Library", "description": "Validation lib"},
    ]
    relations = [
        {"from": "FastAPI", "to": "Python", "type": "USES"},
        {"from": "FastAPI", "to": "Pydantic", "type": "USES"},
    ]
    store.upsert_entities(entities, relations, TEST_NS)
    related = store.query_related(["FastAPI"], TEST_NS, hops=1)
    names = {e["name"] for e in related}
    assert "Python" in names
    assert "Pydantic" in names


def test_query_related_excludes_other_namespaces():
    store = GraphStore()
    other_ns = "other-ns"
    store.clear_namespace(other_ns)
    store.upsert_entities(
        [{"name": "Secret", "type": "Other", "description": "Should not appear"}],
        [],
        other_ns
    )
    store.upsert_entities(
        [{"name": "Python", "type": "Language", "description": "Lang"}],
        [],
        TEST_NS
    )
    related = store.query_related(["Python"], TEST_NS)
    names = {e["name"] for e in related}
    assert "Secret" not in names
    store.clear_namespace(other_ns)


def test_clear_namespace_removes_all_entities():
    store = GraphStore()
    store.upsert_entities(
        [{"name": "ToDelete", "type": "Test", "description": "Will be deleted"}],
        [],
        TEST_NS
    )
    store.clear_namespace(TEST_NS)
    related = store.query_related(["ToDelete"], TEST_NS)
    assert len(related) == 0
