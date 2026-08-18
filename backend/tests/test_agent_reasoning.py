"""Integration tests for agentic reasoning loop."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from app.services.agent import CodeContextAgent
from app.services.query_analyzer import QueryAnalyzer
from app.services.agent_planner import AgentPlanner
from app.services.adaptive_retriever import AdaptiveRetriever
from app.services.answer_validator import AnswerValidator
from app.models.schemas import (
    QueryResponseV2,
    QueryDecomposition,
    SubQuery,
    ValidationResult,
)


@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client."""
    return MagicMock()


@pytest.fixture
def mock_retriever():
    """Create a mock RAGRetriever."""
    mock = MagicMock()
    mock.retrieve.return_value = [
        MagicMock(
            id="chunk1",
            file="auth.py",
            language="python",
            start_line=10,
            end_line=30,
            type="function",
            content="def authenticate(): pass",
            relevance_score=0.95,
        ),
    ]
    return mock


@pytest.fixture
def query_analyzer(mock_anthropic_client):
    """Create QueryAnalyzer."""
    analyzer = QueryAnalyzer(mock_anthropic_client)
    return analyzer


@pytest.fixture
def agent_planner(mock_anthropic_client):
    """Create AgentPlanner."""
    planner = AgentPlanner(mock_anthropic_client)
    return planner


@pytest.fixture
def adaptive_retriever(mock_retriever):
    """Create AdaptiveRetriever."""
    return AdaptiveRetriever(mock_retriever)


@pytest.fixture
def answer_validator(mock_anthropic_client):
    """Create AnswerValidator."""
    return AnswerValidator(mock_anthropic_client)


@pytest.fixture
def agent(mock_anthropic_client, query_analyzer, agent_planner, adaptive_retriever, answer_validator):
    """Create CodeContextAgent with all agentic services."""
    return CodeContextAgent(
        anthropic_client=mock_anthropic_client,
        mcp_server=None,
        model="claude-3-5-sonnet-20241022",
        query_analyzer=query_analyzer,
        agent_planner=agent_planner,
        adaptive_retriever=adaptive_retriever,
        answer_validator=answer_validator,
    )


@pytest.mark.asyncio
async def test_answer_with_reasoning_simple_query(agent, mock_anthropic_client):
    """Test full agentic reasoning loop with simple query."""
    query = "What is authentication?"

    mock_anthropic_client.messages.create.side_effect = [
        MagicMock(
            content=[MagicMock(text='{"is_complex": false, "reasoning": "Simple", "sub_queries": [], "estimated_depth": 1}')]
        ),
        MagicMock(
            content=[
                MagicMock(text='{"retrieval_strategy": {"retrieval_type": "single_round", "max_retrieval_rounds": 1}, "expected_tools": [], "reasoning": "Simple retrieval"}')
            ]
        ),
        MagicMock(
            content=[MagicMock(text="Authentication is a security process...")]
        ),
        MagicMock(
            content=[
                MagicMock(text='{"is_valid": true, "confidence": 0.9, "grounded": true, "hallucination_risk": "low", "missing_aspects": [], "suggestions": null}')
            ]
        ),
    ]

    response = await agent.answer_with_reasoning(query=query)

    assert isinstance(response, QueryResponseV2)
    assert response.answer is not None
    assert len(response.thinking_process) > 0
    assert response.confidence > 0


@pytest.mark.asyncio
async def test_answer_with_reasoning_complex_query(agent, mock_anthropic_client):
    """Test agentic reasoning with complex query."""
    query = "How does auth work and who maintains it?"

    mock_anthropic_client.messages.create.side_effect = [
        MagicMock(
            content=[
                MagicMock(
                    text='{"is_complex": true, "reasoning": "Multi-part", "sub_queries": [{"question": "How auth works", "reasoning": "", "priority": 1}, {"question": "Who maintains", "reasoning": "", "priority": 2}], "estimated_depth": 2}'
                )
            ]
        ),
        MagicMock(
            content=[
                MagicMock(text='{"retrieval_strategy": {"retrieval_type": "iterative", "max_retrieval_rounds": 2}, "expected_tools": ["get_file_blame"], "reasoning": "Complex query"}')
            ]
        ),
        MagicMock(
            content=[MagicMock(text="Authentication implementation...\n\nMaintained by: Security team")]
        ),
        MagicMock(
            content=[
                MagicMock(text='{"is_valid": true, "confidence": 0.85, "grounded": true, "hallucination_risk": "low", "missing_aspects": [], "suggestions": null}')
            ]
        ),
    ]

    response = await agent.answer_with_reasoning(query=query, enable_critique=True)

    assert isinstance(response, QueryResponseV2)
    assert response.query_decomposition is not None
    assert response.query_decomposition.is_complex is True
    assert response.retrieval_rounds > 0
    assert response.validation is not None


@pytest.mark.asyncio
async def test_thinking_steps_captured(agent, mock_anthropic_client):
    """Test that thinking steps are properly captured."""
    query = "Test query"

    mock_anthropic_client.messages.create.side_effect = [
        MagicMock(
            content=[MagicMock(text='{"is_complex": false, "reasoning": "", "sub_queries": [], "estimated_depth": 1}')]
        ),
        MagicMock(
            content=[
                MagicMock(text='{"retrieval_strategy": {"retrieval_type": "single_round", "max_retrieval_rounds": 1}, "expected_tools": [], "reasoning": ""}')
            ]
        ),
        MagicMock(
            content=[MagicMock(text="Answer text")]
        ),
        MagicMock(
            content=[
                MagicMock(text='{"is_valid": true, "confidence": 0.8, "grounded": true, "hallucination_risk": "low", "missing_aspects": [], "suggestions": null}')
            ]
        ),
    ]

    response = await agent.answer_with_reasoning(query=query)

    assert len(response.thinking_process) > 0
    step_types = {step.step_type for step in response.thinking_process}
    assert "plan" in step_types
    assert "retrieve" in step_types
    assert "reason" in step_types
    assert "critique" in step_types
