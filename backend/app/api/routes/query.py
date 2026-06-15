import logging
import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from anthropic import Anthropic

from app.core.config import settings
from app.models.schemas import Citation, QueryRequest, QueryResponse
from app.services.agent import CodeContextAgent
from app.services.mcp_server import MCPGithubServer
from app.services.retriever import RAGRetriever

logger = logging.getLogger(__name__)

router = APIRouter()

# Global singletons — created once on first request
_anthropic_client: Anthropic | None = None
_retriever: RAGRetriever | None = None
_mcp_server: MCPGithubServer | None = None
_agent: CodeContextAgent | None = None


def get_anthropic_client() -> Anthropic:
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _anthropic_client


def get_retriever() -> RAGRetriever:
    global _retriever
    if _retriever is None:
        _retriever = RAGRetriever(
            top_k=settings.RETRIEVER_TOP_K,
            db_path=settings.CHROMA_DB_PATH,
        )
    return _retriever


def get_mcp_server() -> MCPGithubServer | None:
    """Create GitHub MCP server if GITHUB_TOKEN + repo are configured."""
    global _mcp_server
    if _mcp_server is None and (
        settings.GITHUB_TOKEN
        and settings.GITHUB_REPO_OWNER
        and settings.GITHUB_REPO_NAME
    ):
        try:
            _mcp_server = MCPGithubServer(
                github_token=settings.GITHUB_TOKEN,
                repo_owner=settings.GITHUB_REPO_OWNER,
                repo_name=settings.GITHUB_REPO_NAME,
            )
            logger.info(
                f"GitHub MCP server ready: {settings.GITHUB_REPO_OWNER}/{settings.GITHUB_REPO_NAME}"
            )
        except Exception as e:
            logger.warning(f"Failed to initialize GitHub MCP server: {e}")
    return _mcp_server


def get_agent() -> CodeContextAgent:
    global _agent
    if _agent is None:
        _agent = CodeContextAgent(
            anthropic_client=get_anthropic_client(),
            mcp_server=get_mcp_server(),
            model=settings.ANTHROPIC_MODEL,
        )
    return _agent


@router.post("/query", response_model=QueryResponse)
async def query_codebase(
    request: QueryRequest,
    retriever: Annotated[RAGRetriever, Depends(get_retriever)] = None,
    agent: Annotated[CodeContextAgent, Depends(get_agent)] = None,
) -> QueryResponse:
    """
    Ask a question about the indexed codebase.

    Pipeline:
    1. Retrieve top-k similar chunks from ChromaDB
    2. Call Claude with retrieved context
    3. Claude optionally calls MCP tools for live GitHub data
    4. Return answer with citations and confidence score

    Args:
        request: Query with optional parameters

    Returns:
        QueryResponse with answer, citations, and metadata
    """
    start_time = time.time()
    logger.info(f"Processing query: {request.query[:100]}...")

    try:
        retrieved_chunks = retriever.retrieve(
            query=request.query,
            top_k=request.top_k,
            score_threshold=settings.RETRIEVER_SCORE_THRESHOLD,
        )
        logger.info(f"Retrieved {len(retrieved_chunks)} chunks")

        if not retrieved_chunks:
            logger.warning("No relevant chunks found for query")
            return QueryResponse(
                answer=(
                    "I couldn't find relevant code context to answer your question. "
                    "Make sure the codebase has been indexed using the Ingest tab."
                ),
                citations=[],
                mcp_calls=[],
                confidence=0.0,
                processing_time_ms=(time.time() - start_time) * 1000,
            )

        answer, citations, mcp_calls = await agent.answer(
            query=request.query,
            retrieved_chunks=retrieved_chunks,
            use_mcp=request.use_mcp,
        )

        confidence = min(1.0, len(retrieved_chunks) / request.top_k * 0.8 + 0.1)

        return QueryResponse(
            answer=answer,
            citations=citations,
            mcp_calls=mcp_calls,
            confidence=confidence,
            processing_time_ms=(time.time() - start_time) * 1000,
        )

    except Exception as e:
        logger.error(f"Query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
