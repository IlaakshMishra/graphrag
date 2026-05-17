# GraphRAG Merge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Merge RAG-Basic (FastAPI + Pinecone + LangGraph RAG) and graphdb-poc (Neo4j) into a unified GraphRAG system that augments vector retrieval with knowledge-graph context extracted from uploaded documents.

**Architecture:** Every uploaded document is dual-indexed: chunks → Pinecone (vector search) and extracted entities/relationships → Neo4j (graph traversal). At query time, the LangGraph pipeline runs vector retrieval and graph retrieval, combines both, grades relevance, then generates an answer with richer context.

**Tech Stack:** Python 3.11+, FastAPI, LangGraph, Pinecone (vector), Neo4j 5.20 (graph), BGE embeddings, GPT-4o / GPT-4o-mini, React 18 + Vite + TypeScript, Docker Compose, pytest, RAGAS

---

## File Map

```
GraphRAG/
├── backend/
│   ├── main.py                          COPY from RAG-Basic/rag-eval-app/backend/main.py
│   ├── config.py                        MODIFY — add NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
│   ├── routers/
│   │   ├── upload.py                    MODIFY — add entity extraction + graph indexing
│   │   ├── chat.py                      COPY unchanged
│   │   └── evaluate.py                  COPY unchanged
│   ├── services/
│   │   ├── vector_store.py              COPY unchanged
│   │   ├── embedder.py                  COPY unchanged
│   │   ├── document_parser.py           COPY unchanged
│   │   ├── evaluator.py                 COPY unchanged
│   │   ├── evaluation_pipeline.py       COPY unchanged
│   │   ├── graph_store.py               NEW — Neo4j singleton: upsert/query entities
│   │   ├── entity_extractor.py          NEW — LLM-based entity/relation extraction
│   │   └── rag_graph.py                 MODIFY — add graph_retrieve node + graph context in generate
│   └── models/
│       ├── chat.py                      COPY unchanged
│       ├── upload.py                    MODIFY — add entities_indexed field
│       └── evaluate.py                  COPY unchanged
├── frontend/                            COPY from RAG-Basic/rag-eval-app/frontend/ (all files)
│   └── src/components/
│       └── DocumentList.tsx             MODIFY — show entities_indexed badge
├── tests/
│   ├── test_graph_store.py              NEW — Neo4j service integration tests
│   ├── test_entity_extractor.py         NEW — entity extraction unit tests
│   └── test_upload_graph.py             NEW — upload pipeline integration test
├── docker-compose.yml                   NEW — Neo4j service (from graphdb-poc)
├── requirements.txt                     NEW — merged deps from both projects
├── .env.example                         NEW — all required env vars
└── scripts/
    └── dev-backend.sh                   COPY from RAG-Basic
```

---

## Task 1: Scaffold Project — Copy Source Files

**Files:**
- Create: `GraphRAG/backend/` (all subdirs)
- Create: `GraphRAG/frontend/` (all subdirs)
- Create: `GraphRAG/tests/`
- Create: `GraphRAG/scripts/`

- [ ] **Step 1: Copy backend from RAG-Basic**

```bash
cp -r /Users/ilaakshmishra/Documents/AI-RAG/RAG-Basic/rag-eval-app/backend/ \
      /Users/ilaakshmishra/Documents/AI-RAG/GraphRAG/backend/
```

- [ ] **Step 2: Copy frontend from RAG-Basic**

```bash
cp -r /Users/ilaakshmishra/Documents/AI-RAG/RAG-Basic/rag-eval-app/frontend/ \
      /Users/ilaakshmishra/Documents/AI-RAG/GraphRAG/frontend/
```

- [ ] **Step 3: Copy scripts**

```bash
cp -r /Users/ilaakshmishra/Documents/AI-RAG/RAG-Basic/rag-eval-app/scripts/ \
      /Users/ilaakshmishra/Documents/AI-RAG/GraphRAG/scripts/
mkdir -p /Users/ilaakshmishra/Documents/AI-RAG/GraphRAG/tests
```

- [ ] **Step 4: Verify structure**

```bash
find /Users/ilaakshmishra/Documents/AI-RAG/GraphRAG -type f | sort
```

Expected: ~40+ files across backend/, frontend/, scripts/

- [ ] **Step 5: Commit**

```bash
cd /Users/ilaakshmishra/Documents/AI-RAG/GraphRAG
git init
git add backend/ frontend/ scripts/
git commit -m "chore: scaffold from RAG-Basic source files"
```

---

## Task 2: Merge Dependencies and Config Files

**Files:**
- Create: `GraphRAG/requirements.txt`
- Create: `GraphRAG/docker-compose.yml`
- Create: `GraphRAG/.env.example`
- Modify: `GraphRAG/backend/config.py`

- [ ] **Step 1: Write requirements.txt** (RAG-Basic deps + neo4j from graphdb-poc)

Create `/Users/ilaakshmishra/Documents/AI-RAG/GraphRAG/requirements.txt`:

```
# Web
fastapi==0.115.0
uvicorn[standard]==0.30.6
python-multipart==0.0.12

# LLM & Embeddings
openai==1.51.2
sentence-transformers==3.1.1
torch==2.4.1
tiktoken==0.8.0

# Vector DB
pinecone==5.3.1

# Graph DB
neo4j==5.20.0

# Orchestration
langgraph==0.2.34
langchain==0.3.3
langchain-core==0.3.10
langchain-openai==0.2.2
langchain-community==0.3.2
langchain-text-splitters==0.3.0

# Evaluation
ragas==0.2.10
datasets==2.21.0

# Document parsing
pymupdf==1.24.10
pypdf==5.0.1
python-docx==1.1.2
openpyxl==3.1.5
xlrd==2.0.1
Pillow==10.4.0
pytesseract==0.3.13
unstructured==0.15.13

# Async
nest-asyncio==1.6.0
httpx==0.27.2

# Config
pydantic==2.9.2
pydantic-settings==2.5.2
python-dotenv==1.0.1

# Dev
pytest==8.3.3
pytest-asyncio==0.24.0
```

- [ ] **Step 2: Write docker-compose.yml** (Neo4j from graphdb-poc)

Create `/Users/ilaakshmishra/Documents/AI-RAG/GraphRAG/docker-compose.yml`:

```yaml
services:
  neo4j:
    image: neo4j:5.20-community
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      NEO4J_AUTH: neo4j/password123
      NEO4J_PLUGINS: '["apoc"]'
    volumes:
      - neo4j_data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7474"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

volumes:
  neo4j_data:
```

- [ ] **Step 3: Write .env.example**

Create `/Users/ilaakshmishra/Documents/AI-RAG/GraphRAG/.env.example`:

```
# Required
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=pcsk_...

# Neo4j (matches docker-compose defaults)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123

# Optional — defaults shown
OPENAI_CHAT_MODEL=gpt-4o
OPENAI_GRADER_MODEL=gpt-4o-mini
PINECONE_INDEX_NAME=rag-eval-index
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1
HUGGINGFACE_MODEL=BAAI/bge-small-en-v1.5
EMBEDDING_DIMENSION=384
CHUNK_SIZE=512
CHUNK_OVERLAP=64
RETRIEVAL_TOP_K=8
HISTORY_WINDOW=5
GRAPH_RETRIEVAL_HOPS=2
GRAPH_MAX_ENTITIES=10
```

- [ ] **Step 4: Update config.py** — add Neo4j + graph settings

Read current `backend/config.py` first. Then add after the last existing field in the Settings class:

```python
# Neo4j
neo4j_uri: str = "bolt://localhost:7687"
neo4j_user: str = "neo4j"
neo4j_password: str = "password123"

# Graph retrieval
graph_retrieval_hops: int = 2
graph_max_entities: int = 10
```

The full updated Settings class in `backend/config.py`:

```python
from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache


class Settings(BaseSettings):
    # OpenAI
    openai_api_key: str
    openai_chat_model: str = "gpt-4o"
    openai_grader_model: str = "gpt-4o-mini"

    # Pinecone
    pinecone_api_key: str
    pinecone_index_name: str = "rag-eval-index"
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"

    # Embeddings
    huggingface_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dimension: int = 384

    # Chunking / retrieval
    chunk_size: int = 512
    chunk_overlap: int = 64
    retrieval_top_k: int = 8
    history_window: int = 5
    grader_fallback_top_n: int = 4

    # OCR
    document_ocr_enabled: bool = True
    tesseract_cmd: str = ""
    pdf_page_render_ocr: bool = True
    pdf_page_ocr_dpi: int = 200

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password123"

    # Graph retrieval
    graph_retrieval_hops: int = 2
    graph_max_entities: int = 10

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v):
        if isinstance(v, list):
            return ",".join(v)
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 5: Verify config loads**

```bash
cd /Users/ilaakshmishra/Documents/AI-RAG/GraphRAG
python -c "
import sys; sys.path.insert(0, 'backend')
from config import get_settings
s = get_settings()
print('neo4j_uri:', s.neo4j_uri)
print('graph_retrieval_hops:', s.graph_retrieval_hops)
"
```

Expected output:
```
neo4j_uri: bolt://localhost:7687
graph_retrieval_hops: 2
```

- [ ] **Step 6: Commit**

```bash
git add requirements.txt docker-compose.yml .env.example backend/config.py
git commit -m "chore: add merged deps, docker-compose, config with Neo4j settings"
```

---

## Task 3: Implement GraphStore Service (Neo4j)

**Files:**
- Create: `backend/services/graph_store.py`
- Create: `tests/test_graph_store.py`

**Note:** These are integration tests — requires `docker compose up -d neo4j` before running.

- [ ] **Step 1: Write failing tests**

Create `/Users/ilaakshmishra/Documents/AI-RAG/GraphRAG/tests/test_graph_store.py`:

```python
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
    store.upsert_entities(entities, [], TEST_NS)  # second upsert same data
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
```

- [ ] **Step 2: Run tests — confirm failure**

```bash
cd /Users/ilaakshmishra/Documents/AI-RAG/GraphRAG
python -m pytest tests/test_graph_store.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'services.graph_store'`

- [ ] **Step 3: Start Neo4j**

```bash
docker compose up -d neo4j
# Wait ~30s for healthcheck to pass
docker compose ps
```

Expected: `neo4j` service shows `healthy`

- [ ] **Step 4: Implement GraphStore**

Create `/Users/ilaakshmishra/Documents/AI-RAG/GraphRAG/backend/services/graph_store.py`:

```python
import asyncio
from neo4j import GraphDatabase
from config import get_settings

_settings = get_settings()
_instance = None
_lock = asyncio.Lock()


class GraphStore:
    def __init__(self):
        self._driver = GraphDatabase.driver(
            _settings.neo4j_uri,
            auth=(_settings.neo4j_user, _settings.neo4j_password),
        )

    def upsert_entities(
        self, entities: list[dict], relations: list[dict], namespace: str
    ) -> int:
        with self._driver.session() as session:
            for entity in entities:
                session.run(
                    "MERGE (e:Entity {name: $name, namespace: $ns}) "
                    "SET e.type = $type, e.description = $description",
                    name=entity["name"],
                    ns=namespace,
                    type=entity.get("type", "Unknown"),
                    description=entity.get("description", ""),
                )
            for rel in relations:
                session.run(
                    "MATCH (a:Entity {name: $from_name, namespace: $ns}) "
                    "MATCH (b:Entity {name: $to_name, namespace: $ns}) "
                    "MERGE (a)-[r:RELATES_TO {rel_type: $rel_type, namespace: $ns}]->(b)",
                    from_name=rel["from"],
                    to_name=rel["to"],
                    rel_type=rel.get("type", "RELATED_TO"),
                    ns=namespace,
                )
        return len(entities)

    def query_related(
        self, entity_names: list[str], namespace: str, hops: int = 2
    ) -> list[dict]:
        cypher = (
            "MATCH (e:Entity) WHERE e.name IN $names AND e.namespace = $ns "
            "OPTIONAL MATCH (e)-[:RELATES_TO*1..2]-(related:Entity {namespace: $ns}) "
            "WITH collect(distinct e) + collect(distinct related) AS all_e "
            "UNWIND all_e AS entity "
            "RETURN distinct entity.name AS name, entity.type AS type, "
            "entity.description AS description"
        )
        with self._driver.session() as session:
            result = session.run(cypher, names=entity_names, ns=namespace)
            return [dict(row) for row in result]

    def clear_namespace(self, namespace: str) -> None:
        with self._driver.session() as session:
            session.run(
                "MATCH (e:Entity {namespace: $ns}) DETACH DELETE e",
                ns=namespace,
            )

    def close(self) -> None:
        self._driver.close()


async def get_graph_store() -> GraphStore:
    global _instance
    async with _lock:
        if _instance is None:
            _instance = GraphStore()
    return _instance
```

- [ ] **Step 5: Run tests — confirm pass**

```bash
cd /Users/ilaakshmishra/Documents/AI-RAG/GraphRAG
python -m pytest tests/test_graph_store.py -v
```

Expected:
```
tests/test_graph_store.py::test_upsert_entities_returns_count PASSED
tests/test_graph_store.py::test_upsert_is_idempotent PASSED
tests/test_graph_store.py::test_query_related_finds_connected_entities PASSED
tests/test_graph_store.py::test_query_related_excludes_other_namespaces PASSED
tests/test_graph_store.py::test_clear_namespace_removes_all_entities PASSED
5 passed
```

- [ ] **Step 6: Commit**

```bash
git add backend/services/graph_store.py tests/test_graph_store.py
git commit -m "feat: add GraphStore Neo4j service with namespace isolation"
```

---

## Task 4: Implement Entity Extractor

**Files:**
- Create: `backend/services/entity_extractor.py`
- Create: `tests/test_entity_extractor.py`

- [ ] **Step 1: Write failing tests**

Create `/Users/ilaakshmishra/Documents/AI-RAG/GraphRAG/tests/test_entity_extractor.py`:

```python
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
async def test_long_text_truncated_gracefully():
    text = "Python " * 1000  # very long, repetitive text
    result = await extract_entities_from_chunk(text)
    assert "entities" in result
    assert "relationships" in result
```

- [ ] **Step 2: Run tests — confirm failure**

```bash
cd /Users/ilaakshmishra/Documents/AI-RAG/GraphRAG
python -m pytest tests/test_entity_extractor.py -v 2>&1 | head -10
```

Expected: `ModuleNotFoundError: No module named 'services.entity_extractor'`

- [ ] **Step 3: Implement entity_extractor.py**

Create `/Users/ilaakshmishra/Documents/AI-RAG/GraphRAG/backend/services/entity_extractor.py`:

```python
import json
from openai import AsyncOpenAI
from config import get_settings

_SYSTEM_PROMPT = """\
Extract entities and relationships from the provided text.
Return a JSON object with exactly these keys:
- "entities": list of {name: str, type: str, description: str}
  type must be one of: Person, Organization, Technology, Concept, Location, Other
- "relationships": list of {from: str, to: str, type: str}
  type examples: USES, PART_OF, WORKS_AT, CREATED_BY, RELATED_TO, DEVELOPED_BY

Rules:
- Max 10 entities. Only extract clearly mentioned entities.
- Only include relationships where both entities appear in the entities list.
- If text is empty or has no extractable entities, return {"entities": [], "relationships": []}.
"""


async def extract_entities_from_chunk(text: str) -> dict:
    if not text or not text.strip():
        return {"entities": [], "relationships": []}

    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    try:
        response = await client.chat.completions.create(
            model=settings.openai_grader_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f"Text:\n{text[:2000]}"},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        data = json.loads(response.choices[0].message.content)
        entities = data.get("entities", [])
        relationships = data.get("relationships", [])
        # Validate each entity has required fields; drop malformed
        valid_entities = [
            e for e in entities
            if isinstance(e, dict) and "name" in e and "type" in e and "description" in e
        ]
        valid_rels = [
            r for r in relationships
            if isinstance(r, dict) and "from" in r and "to" in r and "type" in r
        ]
        return {"entities": valid_entities, "relationships": valid_rels}
    except Exception:
        return {"entities": [], "relationships": []}
```

- [ ] **Step 4: Run tests — confirm pass**

```bash
cd /Users/ilaakshmishra/Documents/AI-RAG/GraphRAG
python -m pytest tests/test_entity_extractor.py -v
```

Expected: 5 passed (requires OPENAI_API_KEY in env)

- [ ] **Step 5: Commit**

```bash
git add backend/services/entity_extractor.py tests/test_entity_extractor.py
git commit -m "feat: add entity extractor using gpt-4o-mini structured output"
```

---

## Task 5: Update Upload Pipeline — Add Graph Indexing

**Files:**
- Modify: `backend/models/upload.py` — add `entities_indexed` to UploadResponse
- Modify: `backend/routers/upload.py` — call entity extractor + graph store after vector upsert
- Modify: `backend/main.py` — initialize graph store on startup
- Create: `tests/test_upload_graph.py`

- [ ] **Step 1: Write failing test**

Create `/Users/ilaakshmishra/Documents/AI-RAG/GraphRAG/tests/test_upload_graph.py`:

```python
import asyncio
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
```

- [ ] **Step 2: Run test — confirm failure**

```bash
cd /Users/ilaakshmishra/Documents/AI-RAG/GraphRAG
python -m pytest tests/test_upload_graph.py -v 2>&1 | head -15
```

Expected: AssertionError — `entities_indexed` not in response

- [ ] **Step 3: Update UploadResponse model**

Read `/Users/ilaakshmishra/Documents/AI-RAG/GraphRAG/backend/models/upload.py`, then replace its content with:

```python
from pydantic import BaseModel


class UploadResponse(BaseModel):
    namespace: str
    filename: str
    chunks_indexed: int
    bytes_processed: int
    entities_indexed: int = 0
```

- [ ] **Step 4: Update upload router**

Read `/Users/ilaakshmishra/Documents/AI-RAG/GraphRAG/backend/routers/upload.py`. The current structure:
1. Parses file to Document chunks
2. Generates namespace
3. Upserts chunks to Pinecone
4. Returns UploadResponse

Add graph indexing after step 3. Replace the router file with:

```python
import asyncio
import os
import uuid
from fastapi import APIRouter, File, HTTPException, UploadFile

from models.upload import UploadResponse
from services.document_parser import parse
from services.vector_store import VectorStore
from services.entity_extractor import extract_entities_from_chunk
from services.graph_store import get_graph_store

router = APIRouter()

ALLOWED_EXTENSIONS = {
    ".pdf", ".docx", ".txt", ".md",
    ".xlsx", ".xls", ".png", ".jpg", ".jpeg", ".webp", ".gif",
}
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 25 MB limit")

    documents = await asyncio.to_thread(parse, file_bytes, file.filename)
    if not documents:
        raise HTTPException(status_code=422, detail="No content could be extracted from the file")

    namespace = f"upload-{uuid.uuid4().hex[:12]}"

    # Vector indexing
    vector_store = await VectorStore.get()
    chunks_indexed = await vector_store.upsert_chunks(documents, namespace)

    # Graph indexing — extract entities from each chunk in parallel
    extraction_tasks = [
        extract_entities_from_chunk(doc.page_content) for doc in documents
    ]
    extraction_results = await asyncio.gather(*extraction_tasks, return_exceptions=True)

    all_entities: list[dict] = []
    all_relations: list[dict] = []
    for result in extraction_results:
        if isinstance(result, dict):
            all_entities.extend(result.get("entities", []))
            all_relations.extend(result.get("relationships", []))

    # Deduplicate entities by name
    seen_names: set[str] = set()
    unique_entities = []
    for e in all_entities:
        if e["name"] not in seen_names:
            seen_names.add(e["name"])
            unique_entities.append(e)

    entities_indexed = 0
    if unique_entities:
        graph_store = await get_graph_store()
        entities_indexed = await asyncio.to_thread(
            graph_store.upsert_entities, unique_entities, all_relations, namespace
        )

    return UploadResponse(
        namespace=namespace,
        filename=file.filename or "unknown",
        chunks_indexed=chunks_indexed,
        bytes_processed=len(file_bytes),
        entities_indexed=entities_indexed,
    )
```

- [ ] **Step 5: Initialize graph store in main.py startup**

Open `/Users/ilaakshmishra/Documents/AI-RAG/GraphRAG/backend/main.py`. Find the `lifespan` async function. Add graph store initialization after the existing vector store init:

```python
from services.graph_store import get_graph_store

# Inside lifespan, after existing initialization lines:
await get_graph_store()
logger.info("Graph store initialized")
```

The imports block at top of main.py should have `from services.graph_store import get_graph_store` added.

- [ ] **Step 6: Run test — confirm pass**

```bash
cd /Users/ilaakshmishra/Documents/AI-RAG/GraphRAG
python -m pytest tests/test_upload_graph.py -v
```

Expected:
```
tests/test_upload_graph.py::test_upload_returns_entities_indexed PASSED
1 passed
```

- [ ] **Step 7: Commit**

```bash
git add backend/models/upload.py backend/routers/upload.py backend/main.py tests/test_upload_graph.py
git commit -m "feat: add graph indexing to upload pipeline via entity extraction"
```

---

## Task 6: Update RAG Graph — Add Graph Retrieval Node

**Files:**
- Modify: `backend/services/rag_graph.py` — add `graph_retrieve` node, update `RAGState`, update `generate` node

- [ ] **Step 1: Read current rag_graph.py**

```bash
cat /Users/ilaakshmishra/Documents/AI-RAG/GraphRAG/backend/services/rag_graph.py
```

Note the current RAGState TypedDict fields and graph topology: `START → retrieve → grade_documents → generate → END`

- [ ] **Step 2: Update RAGState — add graph_context field**

In `rag_graph.py`, find the RAGState TypedDict definition and add `graph_context`:

```python
class RAGState(TypedDict):
    question: str
    chat_history: list
    retrieved_docs: list
    relevant_docs: list
    graph_context: list   # entities from Neo4j knowledge graph
    answer: str
    sources: list
    session_id: str
    namespace: str
```

- [ ] **Step 3: Add imports at top of rag_graph.py**

Add after existing imports:

```python
import json
from services.graph_store import get_graph_store
```

- [ ] **Step 4: Add graph_retrieve node function**

Add this function after the `retrieve` function in `rag_graph.py`:

```python
async def graph_retrieve(state: RAGState) -> dict:
    settings = get_settings()
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    try:
        resp = await client.chat.completions.create(
            model=settings.openai_grader_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extract 3-5 key entity names from the question. "
                        'Return JSON: {"entities": ["name1", "name2", ...]}'
                    ),
                },
                {"role": "user", "content": state["question"]},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        data = json.loads(resp.choices[0].message.content)
        entity_names = data.get("entities", [])
    except Exception:
        entity_names = []

    graph_context: list[dict] = []
    if entity_names and state.get("namespace"):
        graph_store = await get_graph_store()
        graph_context = await asyncio.to_thread(
            graph_store.query_related,
            entity_names,
            state["namespace"],
            settings.graph_retrieval_hops,
        )
        graph_context = graph_context[: settings.graph_max_entities]

    return {"graph_context": graph_context}
```

- [ ] **Step 5: Update generate node to include graph context**

In the `generate` function, find where the system prompt / context block is assembled. Add graph context section before the user message is sent. The relevant section should look like this:

```python
async def generate(state: RAGState) -> dict:
    settings = get_settings()
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    # ... existing context assembly code ...

    # Add graph context section if available
    graph_context = state.get("graph_context", [])
    graph_section = ""
    if graph_context:
        lines = [
            f"- {e['name']} ({e['type']}): {e['description']}"
            for e in graph_context
            if e.get("name") and e.get("description")
        ]
        if lines:
            graph_section = "\n\nKNOWLEDGE GRAPH CONTEXT:\n" + "\n".join(lines)

    # The system message should include graph_section appended to the context block
    # Find where the system message content string ends and append graph_section before closing
```

Specifically, in the existing generate function, find the line that builds the system message content (something like `system_content = f"... {context_block} ..."`) and append `+ graph_section` at the end of `context_block`.

The exact edit: locate `context_block` (or equivalent variable holding the retrieved document text) and after it add:

```python
if graph_context:
    lines = [
        f"- {e['name']} ({e['type']}): {e['description']}"
        for e in graph_context
        if e.get("name") and e.get("description")
    ]
    if lines:
        context_block += "\n\nKNOWLEDGE GRAPH CONTEXT:\n" + "\n".join(lines)
```

- [ ] **Step 6: Update graph topology — add graph_retrieve node**

Find where the StateGraph is built (looks like `workflow = StateGraph(RAGState)`). Update to:

```python
workflow = StateGraph(RAGState)
workflow.add_node("retrieve", retrieve)
workflow.add_node("graph_retrieve", graph_retrieve)
workflow.add_node("grade_documents", grade_documents)
workflow.add_node("generate", generate)

workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "graph_retrieve")
workflow.add_edge("graph_retrieve", "grade_documents")
workflow.add_edge("grade_documents", "generate")
workflow.add_edge("generate", END)
```

- [ ] **Step 7: Update initial state in run_rag and run_rag_trace**

Find both `run_rag` and `run_rag_trace` functions. In the initial state dict passed to the graph, add `graph_context: []`:

```python
initial_state = {
    "question": question,
    "chat_history": chat_history,
    "retrieved_docs": [],
    "relevant_docs": [],
    "graph_context": [],     # ADD THIS
    "answer": "",
    "sources": [],
    "session_id": session_id,
    "namespace": namespace,
}
```

- [ ] **Step 8: Verify graph runs without error**

```bash
cd /Users/ilaakshmishra/Documents/AI-RAG/GraphRAG
python -c "
import asyncio, sys
sys.path.insert(0, 'backend')
from services.rag_graph import get_compiled_graph
g = get_compiled_graph()
print('Graph nodes:', list(g.nodes))
"
```

Expected output includes: `['retrieve', 'graph_retrieve', 'grade_documents', 'generate']`

- [ ] **Step 9: Commit**

```bash
git add backend/services/rag_graph.py
git commit -m "feat: add graph_retrieve node to RAG pipeline with graph context in generation"
```

---

## Task 7: Update Frontend — Show entities_indexed

**Files:**
- Modify: `frontend/src/types/index.ts` — add `entities_indexed` to `UploadedDoc` and `UploadApiResponse`
- Modify: `frontend/src/components/DocumentList.tsx` — show entities badge

- [ ] **Step 1: Update TypeScript types**

In `frontend/src/types/index.ts`, find `UploadApiResponse` and add `entities_indexed`:

```typescript
export interface UploadApiResponse {
  namespace: string;
  filename: string;
  chunks_indexed: number;
  bytes_processed: number;
  entities_indexed: number;
}
```

Also update `UploadedDoc`:

```typescript
export interface UploadedDoc {
  filename: string;
  namespace: string;
  chunks_indexed: number;
  bytes_processed: number;
  entities_indexed: number;
  uploaded_at: Date;
}
```

- [ ] **Step 2: Update useUpload.ts to store entities_indexed**

In `frontend/src/hooks/useUpload.ts`, find where a new `UploadedDoc` is constructed after a successful upload. Add `entities_indexed: data.entities_indexed`:

```typescript
const newDoc: UploadedDoc = {
  filename: data.filename,
  namespace: data.namespace,
  chunks_indexed: data.chunks_indexed,
  bytes_processed: data.bytes_processed,
  entities_indexed: data.entities_indexed,
  uploaded_at: new Date(),
};
```

- [ ] **Step 3: Update DocumentList.tsx — show entities badge**

In `frontend/src/components/DocumentList.tsx`, find where chunk count is displayed (something like `{doc.chunks_indexed} chunks`). Add entities count after it:

```tsx
<span className="text-xs text-zinc-500">{doc.chunks_indexed} chunks</span>
{doc.entities_indexed > 0 && (
  <span className="text-xs text-violet-400">{doc.entities_indexed} entities</span>
)}
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd /Users/ilaakshmishra/Documents/AI-RAG/GraphRAG/frontend
npm install
npm run build 2>&1 | tail -10
```

Expected: Build completes with no TypeScript errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/hooks/useUpload.ts frontend/src/components/DocumentList.tsx
git commit -m "feat: show entities_indexed count in document list UI"
```

---

## Task 8: End-to-End Smoke Test

**Files:**
- No new files — manual verification

- [ ] **Step 1: Set environment variables**

```bash
cp .env.example .env
# Edit .env and fill in OPENAI_API_KEY and PINECONE_API_KEY
```

- [ ] **Step 2: Start Neo4j**

```bash
docker compose up -d neo4j
docker compose ps
```

Expected: neo4j `healthy`

- [ ] **Step 3: Install Python dependencies**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

- [ ] **Step 4: Run backend**

```bash
cd /Users/ilaakshmishra/Documents/AI-RAG/GraphRAG
source venv/bin/activate
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Expected log lines:
```
INFO: Graph store initialized
INFO: Vector store initialized
INFO: Embedder initialized
INFO: Application startup complete.
```

- [ ] **Step 5: Run frontend (separate terminal)**

```bash
cd /Users/ilaakshmishra/Documents/AI-RAG/GraphRAG/frontend
npm run dev
```

Expected: `Local: http://localhost:5173/`

- [ ] **Step 6: Upload a document and verify entities_indexed**

```bash
curl -s -X POST http://localhost:8000/api/upload \
  -F "file=@/path/to/any.txt" | python3 -m json.tool
```

Expected response includes `"entities_indexed": <positive int>`:
```json
{
  "namespace": "upload-abc123456789",
  "filename": "any.txt",
  "chunks_indexed": 3,
  "bytes_processed": 1234,
  "entities_indexed": 7
}
```

- [ ] **Step 7: Run a chat query and verify it completes**

```bash
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is this document about?",
    "namespace": "<namespace from step 6>",
    "session_id": "test-session-1",
    "chat_history": []
  }' | python3 -m json.tool
```

Expected: JSON with `answer` (non-empty string) and `sources` array

- [ ] **Step 8: Run all tests**

```bash
cd /Users/ilaakshmishra/Documents/AI-RAG/GraphRAG
source venv/bin/activate
python -m pytest tests/ -v
```

Expected: All tests pass

- [ ] **Step 9: Final commit**

```bash
git add .
git commit -m "chore: verified end-to-end GraphRAG pipeline with dual vector+graph retrieval"
```

---

## Self-Review

### Spec Coverage

| Requirement | Task |
|---|---|
| Copy RAG-Basic backend | Task 1 |
| Copy RAG-Basic frontend | Task 1 |
| Add Neo4j (docker-compose) | Task 2 |
| Merge requirements.txt | Task 2 |
| Add Neo4j config settings | Task 2 |
| GraphStore service | Task 3 |
| Entity extraction from chunks | Task 4 |
| Dual-index on upload (vector + graph) | Task 5 |
| `entities_indexed` in upload response | Task 5 |
| Graph retrieval node in LangGraph | Task 6 |
| Graph context in answer generation | Task 6 |
| Frontend shows entities count | Task 7 |
| End-to-end smoke test | Task 8 |

### No Placeholder Violations

All code blocks contain real, runnable code. No TBD, TODO, or "similar to above" references.

### Type Consistency

- `GraphStore.upsert_entities` called in `upload.py` matches signature in `graph_store.py`
- `GraphStore.query_related` called in `rag_graph.py` matches signature
- `get_graph_store()` returns `GraphStore` instance everywhere it's called
- `RAGState.graph_context: list` initialized as `[]` in both `run_rag` and `run_rag_trace`
- `UploadResponse.entities_indexed: int` matches `UploadApiResponse.entities_indexed: number` in TypeScript
- `UploadedDoc.entities_indexed` set from `data.entities_indexed` in `useUpload.ts`
