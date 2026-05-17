import os
os.environ.setdefault("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", "test-key"))
os.environ.setdefault("PINECONE_API_KEY", "test-pinecone-key")

import pytest
import sys
sys.path.insert(0, "backend")

from httpx import AsyncClient, ASGITransport
from main import app

TEST_TXT = b"Python is a programming language. Pinecone is a vector database. RAG uses both."


@pytest.mark.asyncio
async def test_upload_returns_entities_indexed():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/upload",
            files={"file": ("test.txt", TEST_TXT, "text/plain")},
        )
    assert response.status_code == 200
    data = response.json()
    assert "entities_indexed" in data
    assert isinstance(data["entities_indexed"], int)
    assert data["entities_indexed"] >= 0
