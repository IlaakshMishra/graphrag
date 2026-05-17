"""FastAPI entry point.

Run locally with:
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from backend.config import get_settings
from backend.routers import chat, evaluate, upload
from backend.services import document_parser, embedder
from backend.services.vector_store import VectorStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("rag-eval")


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_settings()
    logger.info("Booting rag-eval API …")
    embedder.warmup()
    document_parser.log_ocr_status_at_startup()
    VectorStore.get()
    logger.info(
        "Ready. index=%s dim=%d cors=%s",
        cfg.PINECONE_INDEX_NAME,
        cfg.EMBEDDING_DIMENSION,
        cfg.cors_origin_list,
    )
    yield
    logger.info("Shutting down")


def create_app() -> FastAPI:
    cfg = get_settings()
    app = FastAPI(
        title="Conversational RAG with RAGAS Evaluation",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(upload.router, prefix="/api")
    app.include_router(chat.router, prefix="/api")
    app.include_router(evaluate.router, prefix="/api")

    @app.get("/", tags=["meta"], response_class=HTMLResponse)
    async def root_landing() -> str:
        """Browser hits port 8000 — without this route the page looks ‘blank’."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>RAG Eval API</title>
  <style>
    :root { color-scheme: dark; }
    body { font-family: ui-sans-serif, system-ui, sans-serif; margin: 0; min-height: 100vh;
      background: #0a0a0c; color: #e4e4e7; display: flex; align-items: center; justify-content: center;
      padding: 2rem; }
    .card { max-width: 36rem; border: 1px solid #27272a; border-radius: 0.75rem; padding: 1.75rem;
      background: #111114; }
    h1 { margin: 0 0 0.5rem; font-size: 1.25rem; font-weight: 600; }
    p { margin: 0 0 1rem; color: #a1a1aa; font-size: 0.875rem; line-height: 1.6; }
    ul { margin: 0 0 1rem; padding-left: 1.25rem; color: #a1a1aa; font-size: 0.875rem; line-height: 1.8; }
    a { color: #a78bfa; text-decoration: none; }
    a:hover { text-decoration: underline; }
    code { background: #18181b; padding: 0.15rem 0.4rem; border-radius: 0.25rem; font-size: 0.8rem; }
    .links { display: flex; flex-wrap: wrap; gap: 0.75rem; margin-top: 1rem; }
    .pill { border: 1px solid #3f3f46; padding: 0.35rem 0.65rem; border-radius: 9999px; font-size: 0.75rem; }
  </style>
</head>
<body>
  <div class="card">
    <h1>Conversational RAG API</h1>
    <p>This server exposes JSON endpoints under <code>/api/*</code>. OpenAPI docs live at <a href="/docs">/docs</a>.</p>
    <p><strong>Web UI:</strong> run the Vite app and open <code>http://localhost:5173</code> — it proxies API calls to this backend.</p>
    <ul>
      <li><a href="/docs">Swagger UI</a> — try <code>POST /api/upload</code>, <code>POST /api/chat</code></li>
      <li><a href="/redoc">ReDoc</a></li>
      <li><a href="/api/health">GET /api/health</a></li>
    </ul>
    <div class="links">
      <span class="pill">FastAPI</span>
      <span class="pill">LangGraph</span>
      <span class="pill">Pinecone</span>
      <span class="pill">RAGAS</span>
    </div>
  </div>
</body>
</html>"""

    @app.get("/api/health", tags=["meta"])
    async def health() -> dict:
        return {"status": "ok"}

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        logger.exception("unhandled error on %s %s", request.method, request.url)
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "detail": str(exc)},
        )

    return app


app = create_app()
