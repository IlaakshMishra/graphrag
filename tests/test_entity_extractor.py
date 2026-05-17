import os
os.environ.setdefault("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", "test-key"))
os.environ.setdefault("PINECONE_API_KEY", "test-pinecone-key")

import asyncio
import pytest
import sys
sys.path.insert(0, "backend")

from services.entity_extractor import extract_entities_from_chunk


@pytest.mark.asyncio
async def test_extracts_entities_from_text():
    text = "Python is a programming language. FastAPI is a Python web framework built by Sebastián Ramírez."
    result = await extract_entities_from_chunk(text)
    assert "entities" in result
    assert "relationships" in result
    assert isinstance(result["entities"], list)
    assert isinstance(result["relationships"], list)
    assert len(result["entities"]) >= 2
    names = {e["name"] for e in result["entities"]}
    assert "Python" in names or "FastAPI" in names


@pytest.mark.asyncio
async def test_each_entity_has_required_fields():
    text = "Langchain is a framework for building LLM applications."
    result = await extract_entities_from_chunk(text)
    for entity in result["entities"]:
        assert "name" in entity
        assert "type" in entity
        assert "description" in entity


@pytest.mark.asyncio
async def test_each_relationship_has_required_fields():
    text = "FastAPI uses Pydantic for data validation."
    result = await extract_entities_from_chunk(text)
    for rel in result["relationships"]:
        assert "from" in rel
        assert "to" in rel
        assert "type" in rel


@pytest.mark.asyncio
async def test_empty_text_returns_empty_lists():
    result = await extract_entities_from_chunk("")
    assert result == {"entities": [], "relationships": []}


@pytest.mark.asyncio
async def test_whitespace_only_returns_empty_lists():
    result = await extract_entities_from_chunk("   \n\t  ")
    assert result == {"entities": [], "relationships": []}
