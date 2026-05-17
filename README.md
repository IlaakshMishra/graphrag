# GraphRAG

A Graph-Augmented Retrieval system that combines vector search (Pinecone) with a knowledge graph (Neo4j) to deliver richer, more accurate answers from your documents.

Merged from two projects:
- **RAG-Basic** — FastAPI + Pinecone + LangGraph RAG pipeline with RAGAS evaluation
- **graphdb-poc** — Neo4j knowledge graph with Cypher query patterns

---

## How It Works

### Upload Flow

```
Document → Parse (PDF/DOCX/TXT/XLSX/Images with OCR)
         → Chunk (512 chars, 64 overlap)
         → Embed (BGE-small-en-v1.5, local)
         → Pinecone (vector search)
         → GPT-4o-mini (extract entities & relations)
         → Neo4j (knowledge graph, namespace-isolated)
```

### Query Flow

```
Question → LangGraph Pipeline:
  1. retrieve        — vector search in Pinecone (top-8 chunks)
  2. graph_retrieve  — extract key entities from question → Neo4j traversal (1–5 hops)
  3. grade_documents — GPT-4o-mini relevance filter on retrieved chunks
  4. generate        — GPT-4o answer with vector context + graph entity context
```

### Evaluation

RAGAS metrics: faithfulness, answer relevancy, context precision, context recall. Run against raw Q&A batches or live RAG pipeline.

---

## Architecture

```
GraphRAG/
├── backend/
│   ├── main.py                    FastAPI app, lifespan startup
│   ├── config.py                  All settings (env vars + defaults)
│   ├── routers/
│   │   ├── upload.py              POST /api/upload
│   │   ├── chat.py                POST /api/chat
│   │   └── evaluate.py            POST /api/evaluate, /api/evaluate/pipeline
│   ├── services/
│   │   ├── graph_store.py         Neo4j singleton — upsert/query entities
│   │   ├── entity_extractor.py    GPT-4o-mini structured entity/relation extraction
│   │   ├── rag_graph.py           LangGraph: retrieve → graph_retrieve → grade → generate
│   │   ├── vector_store.py        Pinecone singleton — upsert/query chunks
│   │   ├── embedder.py            BGE sentence-transformers (local)
│   │   ├── document_parser.py     PDF/DOCX/TXT/XLSX/Image parser with OCR
│   │   ├── evaluator.py           RAGAS evaluation runner
│   │   └── evaluation_pipeline.py End-to-end RAG + RAGAS
│   └── models/                    Pydantic request/response schemas
├── frontend/                      React 18 + Vite + TypeScript + Tailwind
│   └── src/
│       ├── components/            ChatWindow, UploadZone, DocumentList, EvalPanel
│       ├── hooks/                 useChat, useUpload
│       ├── api/client.ts          Axios HTTP client
│       └── types/index.ts         TypeScript interfaces
├── tests/
│   ├── test_graph_store.py        Neo4j service integration tests
│   ├── test_entity_extractor.py   Entity extraction unit tests
│   └── test_upload_graph.py       Upload pipeline integration test
├── docker-compose.yml             Neo4j 5.20-community
├── requirements.txt               Python dependencies
└── .env.example                   Environment variable template
```

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11+ | Tested on 3.12 |
| Node.js | 18+ | For frontend |
| Docker | any recent | For Neo4j |
| Tesseract | optional | OCR for PDFs with images/diagrams — `brew install tesseract` |

API keys required:
- **OpenAI** — chat generation + entity extraction + relevance grading
- **Pinecone** — serverless vector index (free tier works)

---

## Setup

### 1. Environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in the two required values:

```
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=pcsk_...
```

Everything else has sensible defaults. Neo4j credentials match the docker-compose service.

### 2. Start Neo4j

```bash
docker compose up -d neo4j
```

Wait ~30 seconds for the healthcheck to pass:

```bash
docker compose ps
# neo4j should show "healthy"
```

Neo4j browser available at http://localhost:7474 (credentials: `neo4j` / `password123`).

### 3. Backend

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the API server
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Swagger docs available at http://localhost:8000/docs

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

App available at http://localhost:5173

---

## Usage

### Chat with a document

1. Open http://localhost:5173
2. Drag and drop a file into the upload zone (PDF, DOCX, TXT, MD, XLSX, XLS, PNG, JPG — max 25 MB)
3. Wait for indexing — the document card shows chunk count and entity count (e.g. `12 chunks · 7 entities`)
4. Click the document to make it active
5. Type your question and hit Send

### Evaluate RAG quality

Click the **Evaluate** tab:
- **Simple evaluate** — paste questions, answers, and contexts; get RAGAS scores
- **Pipeline evaluate** — enter questions against an uploaded namespace; runs full RAG then scores

### API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/upload` | Upload document, returns `namespace` + `entities_indexed` |
| POST | `/api/chat` | Chat with a namespace, returns `answer` + `sources` |
| POST | `/api/evaluate` | Batch RAGAS evaluation |
| POST | `/api/evaluate/pipeline` | Live RAG + RAGAS evaluation |
| GET  | `/api/health` | Health check |

---

## Configuration

All settings are environment variables. Defaults are production-friendly for development.

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | **Required** |
| `PINECONE_API_KEY` | — | **Required** |
| `OPENAI_CHAT_MODEL` | `gpt-4o` | Generation model |
| `OPENAI_GRADER_MODEL` | `gpt-4o-mini` | Relevance grading + entity extraction |
| `PINECONE_INDEX_NAME` | `rag-eval-index` | Created automatically on first run |
| `PINECONE_CLOUD` | `aws` | |
| `PINECONE_REGION` | `us-east-1` | |
| `NEO4J_URI` | `bolt://localhost:7687` | |
| `NEO4J_USER` | `neo4j` | |
| `NEO4J_PASSWORD` | `password123` | Change this in production |
| `GRAPH_RETRIEVAL_HOPS` | `2` | Graph traversal depth (1–5) |
| `GRAPH_MAX_ENTITIES` | `10` | Max entity context injected per query |
| `RETRIEVAL_TOP_K` | `8` | Chunks retrieved from Pinecone per query |
| `CHUNK_SIZE` | `512` | Characters per chunk |
| `CHUNK_OVERLAP` | `64` | Overlap between chunks |
| `DOCUMENT_OCR_ENABLED` | `true` | Tesseract OCR for images in PDFs |
| `TESSERACT_CMD` | auto-detected | Absolute path to Tesseract binary if not on PATH |

---

## Tests

```bash
# Unit tests — no services required
python -m pytest tests/test_entity_extractor.py -k "empty or whitespace" -v

# Integration tests — requires Neo4j running
python -m pytest tests/test_graph_store.py -v

# All tests
python -m pytest tests/ -v
```

---

## Supported File Formats

| Format | Notes |
|--------|-------|
| PDF | Text extraction + table detection + embedded image OCR + vector diagram OCR |
| DOCX | Paragraphs + tables |
| TXT / MD | Plain text |
| XLSX / XLS | Sheets converted to tables |
| PNG / JPG / JPEG / WEBP / GIF | Full OCR via Tesseract |

---

## Key Design Decisions

**Dual indexing on upload** — every document is indexed in both Pinecone (fast vector search) and Neo4j (entity graph). If Neo4j is down, the upload still succeeds with `entities_indexed: 0`; vector retrieval works normally.

**Namespace isolation** — each upload gets a UUID namespace (`upload-<12hex>`). Pinecone vectors and Neo4j entities are scoped to this namespace; no cross-document leakage.

**Graph retrieval fallback** — if entity extraction returns nothing or Neo4j is unreachable at query time, the pipeline continues with vector-only context. The graph layer enhances answers, never blocks them.

**BGE query-instruction prefix** — queries are prefixed with `"Represent this sentence for searching relevant passages: "` before embedding; documents are not. This asymmetry is required for accurate BGE retrieval recall.

---

## Knowledge Graph Visualization

After uploading a document, run this in the Neo4j browser (http://localhost:7474) to visualize the full entity graph:

```cypher
MATCH path = (a:Entity {namespace: "upload-<your-namespace>"})-[:RELATES_TO*1..2]-(b:Entity)
RETURN path
```

Replace `upload-<your-namespace>` with the namespace shown in the document list (e.g. `upload-f2ce3cfff813`).

The result is an interactive force-directed graph where each node is an extracted entity and each edge is a relationship between them. Example output from a real document upload — **231 entities, 392 relationships**:

![Neo4j knowledge graph — 231 nodes, 392 relationships](assets/Screenshot%202026-05-17%20at%209.56.41%20AM.png)

Other useful queries in Neo4j browser:

```cypher
-- List all entities with type
MATCH (e:Entity {namespace: "upload-<your-namespace>"})
RETURN e.name, e.type, e.description
ORDER BY e.type

-- Show all relationships as a table
MATCH (a:Entity)-[r:RELATES_TO]->(b:Entity {namespace: "upload-<your-namespace>"})
RETURN a.name, r.rel_type, b.name

-- Count entities and relationships
MATCH (e:Entity {namespace: "upload-<your-namespace>"})
OPTIONAL MATCH (e)-[r:RELATES_TO]->()
RETURN count(distinct e) AS entities, count(r) AS relationships
```

---

## Troubleshooting

**Backend won't start — `OPENAI_API_KEY` missing**
Make sure `.env` exists in the `GraphRAG/` root with `OPENAI_API_KEY` and `PINECONE_API_KEY` set.

**Neo4j connection refused**
Run `docker compose up -d neo4j` and wait 30 seconds. Check `docker compose ps` shows `healthy`.

**Tesseract not found (OCR disabled)**
Install with `brew install tesseract` (macOS) or `apt-get install tesseract-ocr` (Linux). If the binary is not on PATH, set `TESSERACT_CMD=/opt/homebrew/bin/tesseract` in `.env`.

**Pinecone index not found**
The index is created automatically on first backend startup. If you changed `PINECONE_INDEX_NAME`, let the backend start once to create it.

**`entities_indexed: 0` after upload**
Either Neo4j is not running, or entity extraction failed (check backend logs). The document is still searchable via vector retrieval.
