import logging
import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from anthropic import Anthropic

from ...core.config import settings
from ...models.schemas import QueryRequest, QueryResponseV2
from ...services.agent import CodeContextAgent
from ...services.answer_validator import AnswerValidator
from ...services.adaptive_retriever import AdaptiveRetriever
from ...services.agent_planner import AgentPlanner
from ...services.query_analyzer import QueryAnalyzer
from ...services.mcp_server import MCPGithubServer
from ...services.retriever import RAGRetriever
from ...services.embedder_factory import create_embedder

logger = logging.getLogger(__name__)

router = APIRouter()

# Global singletons — created once on first request
_anthropic_client: Anthropic | None = None
_retriever: RAGRetriever | None = None
_mcp_server: MCPGithubServer | None = None
_query_analyzer: QueryAnalyzer | None = None
_agent_planner: AgentPlanner | None = None
_adaptive_retriever: AdaptiveRetriever | None = None
_answer_validator: AnswerValidator | None = None
_agent: CodeContextAgent | None = None


def get_anthropic_client() -> Anthropic:
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _anthropic_client


def get_retriever() -> RAGRetriever:
    global _retriever
    if _retriever is None:
        embeddings = create_embedder()
        _retriever = RAGRetriever(
            embeddings=embeddings,
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


def get_query_analyzer() -> QueryAnalyzer | None:
    """Create QueryAnalyzer if agent V2 is enabled."""
    global _query_analyzer
    if settings.ENABLE_AGENT_V2 and _query_analyzer is None:
        _query_analyzer = QueryAnalyzer(
            anthropic_client=get_anthropic_client(),
            model=settings.ANTHROPIC_MODEL,
        )
    return _query_analyzer if settings.ENABLE_AGENT_V2 else None


def get_agent_planner() -> AgentPlanner | None:
    """Create AgentPlanner if agent V2 is enabled."""
    global _agent_planner
    if settings.ENABLE_AGENT_V2 and _agent_planner is None:
        _agent_planner = AgentPlanner(
            anthropic_client=get_anthropic_client(),
            model=settings.ANTHROPIC_MODEL,
        )
    return _agent_planner if settings.ENABLE_AGENT_V2 else None


def get_adaptive_retriever() -> AdaptiveRetriever | None:
    """Create AdaptiveRetriever if agent V2 is enabled."""
    global _adaptive_retriever
    if settings.ENABLE_AGENT_V2 and _adaptive_retriever is None:
        _adaptive_retriever = AdaptiveRetriever(
            retriever=get_retriever(),
        )
    return _adaptive_retriever if settings.ENABLE_AGENT_V2 else None


def get_answer_validator() -> AnswerValidator | None:
    """Create AnswerValidator if agent V2 and critique are enabled."""
    global _answer_validator
    if settings.ENABLE_AGENT_V2 and settings.AGENT_ENABLE_SELF_CRITIQUE and _answer_validator is None:
        _answer_validator = AnswerValidator(
            anthropic_client=get_anthropic_client(),
            model=settings.ANTHROPIC_MODEL,
        )
    return _answer_validator if (
        settings.ENABLE_AGENT_V2 and settings.AGENT_ENABLE_SELF_CRITIQUE
    ) else None


def get_agent(
    query_analyzer: Annotated[QueryAnalyzer | None, Depends(get_query_analyzer)] = None,
    agent_planner: Annotated[AgentPlanner | None, Depends(get_agent_planner)] = None,
    adaptive_retriever: Annotated[AdaptiveRetriever | None, Depends(get_adaptive_retriever)] = None,
    answer_validator: Annotated[AnswerValidator | None, Depends(get_answer_validator)] = None,
) -> CodeContextAgent:
    """Create enhanced CodeContextAgent with optional agentic services."""
    global _agent
    if _agent is None:
        _agent = CodeContextAgent(
            anthropic_client=get_anthropic_client(),
            mcp_server=get_mcp_server(),
            model=settings.ANTHROPIC_MODEL,
            query_analyzer=query_analyzer,
            agent_planner=agent_planner,
            adaptive_retriever=adaptive_retriever,
            answer_validator=answer_validator,
        )
    return _agent


@router.post("/query", response_model=QueryResponseV2)
async def query_codebase(
    request: QueryRequest,
    agent: Annotated[CodeContextAgent, Depends(get_agent)] = None,
) -> QueryResponseV2:
    """
    Ask a question about the indexed codebase using agentic reasoning.

    When ENABLE_AGENT_V2=true (default), uses ReAct pattern:
    1. PLAN: Analyze query complexity, decompose if needed
    2. PLAN: Decide retrieval strategy and tools
    3. RETRIEVE: Adaptive (possibly multi-step) context retrieval
    4. REASON: Synthesize answer with Claude + optional MCP tools
    5. CRITIQUE: Validate answer against context (optional)
    6. REFLECT: Return answer with visible reasoning steps

    When ENABLE_AGENT_V2=false, falls back to simple RAG pipeline.

    Args:
        request: Query with optional parameters

    Returns:
        QueryResponseV2 with answer, citations, thinking process, and validation
    """
    start_time = time.time()
    logger.info(
        f"Processing query (Agent V2: {settings.ENABLE_AGENT_V2}): {request.query[:100]}..."
    )

    try:
        if settings.ENABLE_AGENT_V2 and agent.query_analyzer:
            response = await agent.answer_with_reasoning(
                query=request.query,
                use_mcp=request.use_mcp,
                enable_critique=settings.AGENT_ENABLE_SELF_CRITIQUE,
            )
            logger.info(f"Agentic reasoning complete. Confidence: {response.confidence:.2f}")
            return response

        else:
            logger.info("Using fallback simple RAG pipeline")
            from ...services.retriever import RAGRetriever
            retriever = get_retriever()

            retrieved_chunks = retriever.retrieve(
                query=request.query,
                top_k=request.top_k,
                score_threshold=settings.RETRIEVER_SCORE_THRESHOLD,
            )
            logger.info(f"Retrieved {len(retrieved_chunks)} chunks")

            if not retrieved_chunks:
                logger.warning("No relevant chunks found for query")
                return QueryResponseV2(
                    answer=(
                        "I couldn't find relevant code context to answer your question. "
                        "Make sure the codebase has been indexed using the Ingest tab."
                    ),
                    citations=[],
                    mcp_calls=[],
                    confidence=0.0,
                    processing_time_ms=(time.time() - start_time) * 1000,
                    thinking_process=[],
                    query_decomposition=None,
                    validation=None,
                    retrieval_rounds=0,
                    num_retrieval_queries=0,
                )

            answer, citations, mcp_calls = await agent.answer(
                query=request.query,
                retrieved_chunks=retrieved_chunks,
                use_mcp=request.use_mcp,
            )

            confidence = min(1.0, len(retrieved_chunks) / request.top_k * 0.8 + 0.1)

            return QueryResponseV2(
                answer=answer,
                citations=citations,
                mcp_calls=mcp_calls,
                confidence=confidence,
                processing_time_ms=(time.time() - start_time) * 1000,
                thinking_process=[],
                query_decomposition=None,
                validation=None,
                retrieval_rounds=1,
                num_retrieval_queries=1,
            )

    except Exception as e:
        logger.error(f"Query failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
