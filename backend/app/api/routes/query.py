import logging
import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from anthropic import Anthropic

from app.core.config import settings
from app.models.schemas import Citation, QueryRequest, QueryResponse
from app.services.agent import CodeContextAgent
from app.services.retriever import RAGRetriever

logger = logging.getLogger(__name__)

router = APIRouter()

# Global client instances
_anthropic_client = None
_retriever = None
_agent = None


def get_anthropic_client():
    """Get or create Anthropic client."""
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _anthropic_client


def get_retriever():
    """Get or create retriever instance."""
    global _retriever
    if _retriever is None:
        _retriever = RAGRetriever(
            top_k=settings.RETRIEVER_TOP_K,
            db_path=settings.CHROMA_DB_PATH,
        )
    return _retriever


def get_agent():
    """Get or create agent instance."""
    global _agent
    if _agent is None:
        client = get_anthropic_client()
        _agent = CodeContextAgent(anthropic_client=client)
    return _agent


@router.post("/query", response_model=QueryResponse)
async def query_codebase(
    request: QueryRequest,
    client: Annotated[Anthropic, Depends(get_anthropic_client)] = None,
    retriever: Annotated[RAGRetriever, Depends(get_retriever)] = None,
    agent: Annotated[CodeContextAgent, Depends(get_agent)] = None,
) -> QueryResponse:
    """
    Ask a question about the indexed codebase.

    This endpoint:
    1. Encodes the query with Anthropic embeddings
    2. Retrieves top-k similar chunks from ChromaDB
    3. Calls LLM agent (Claude) with retrieved context
    4. Agent optionally calls MCP tools (GitHub API)
    5. Returns answer with citations and confidence

    Args:
        request: Query with optional parameters

    Returns:
        QueryResponse with answer, citations, and metadata
    """
    start_time = time.time()
    logger.info(f"Processing query: {request.query[:100]}...")

    try:
        # Retrieve relevant code chunks
        retrieved_chunks = retriever.retrieve(
            query=request.query,
            top_k=request.top_k,
            score_threshold=settings.RETRIEVER_SCORE_THRESHOLD,
        )

        logger.info(f"Retrieved {len(retrieved_chunks)} chunks")

        # If no chunks found, provide a helpful message
        if not retrieved_chunks:
            logger.warning("No relevant chunks found for query")
            processing_time = (time.time() - start_time) * 1000
            return QueryResponse(
                answer="I couldn't find relevant code context to answer your question. "
                "Make sure the codebase has been indexed using the /api/v1/ingest endpoint.",
                citations=[],
                mcp_calls=[],
                confidence=0.0,
                processing_time_ms=processing_time,
            )

        # Generate answer using agent
        answer, citations, mcp_calls = await agent.answer(
            query=request.query,
            retrieved_chunks=retrieved_chunks,
            use_mcp=request.use_mcp,
        )

        # Calculate confidence based on number of chunks and answer length
        confidence = min(1.0, len(retrieved_chunks) / request.top_k * 0.8 + 0.1)

        processing_time = (time.time() - start_time) * 1000

        return QueryResponse(
            answer=answer,
            citations=citations,
            mcp_calls=mcp_calls,
            confidence=confidence,
            processing_time_ms=processing_time,
        )

    except Exception as e:
        logger.error(f"Query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
