"""Unit tests for QueryAnalyzer service."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.query_analyzer import QueryAnalyzer
from app.models.schemas import QueryDecomposition


@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client."""
    return MagicMock()


@pytest.fixture
def query_analyzer(mock_anthropic_client):
    """Create a QueryAnalyzer instance with mock client."""
    return QueryAnalyzer(
        anthropic_client=mock_anthropic_client,
        model="claude-3-5-sonnet-20241022",
    )


@pytest.mark.asyncio
async def test_analyze_simple_query(query_analyzer, mock_anthropic_client):
    """Test analyzing a simple (non-complex) query."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock()]
    mock_response.content[0].text = '{"is_complex": false, "reasoning": "Simple single question", "sub_queries": [], "estimated_depth": 1}'

    mock_anthropic_client.messages.create.return_value = mock_response

    decomposition = await query_analyzer.analyze_query("What is the purpose of this function?")

    assert isinstance(decomposition, QueryDecomposition)
    assert decomposition.is_complex is False
    assert len(decomposition.sub_queries) == 0
    assert decomposition.estimated_depth == 1


@pytest.mark.asyncio
async def test_analyze_complex_query(query_analyzer, mock_anthropic_client):
    """Test analyzing a complex (multi-part) query."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock()]
    mock_response.content[0].text = '''{
        "is_complex": true,
        "reasoning": "Query asks two separate things",
        "sub_queries": [
            {"question": "How does authentication work?", "reasoning": "First part", "priority": 1},
            {"question": "Who maintains the auth code?", "reasoning": "Second part", "priority": 2}
        ],
        "estimated_depth": 2
    }'''

    mock_anthropic_client.messages.create.return_value = mock_response

    decomposition = await query_analyzer.analyze_query(
        "How does authentication work and who maintains the code?"
    )

    assert decomposition.is_complex is True
    assert len(decomposition.sub_queries) == 2
    assert decomposition.sub_queries[0].priority == 1
    assert decomposition.estimated_depth == 2


@pytest.mark.asyncio
async def test_analyze_query_fallback_on_error(query_analyzer, mock_anthropic_client):
    """Test fallback behavior when Claude returns invalid JSON."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock()]
    mock_response.content[0].text = "Not valid JSON"

    mock_anthropic_client.messages.create.return_value = mock_response

    decomposition = await query_analyzer.analyze_query("Some query")

    assert isinstance(decomposition, QueryDecomposition)
    assert decomposition.original_query == "Some query"
