"""Unit tests for AnswerValidator service."""

import pytest
from unittest.mock import MagicMock

from app.services.answer_validator import AnswerValidator
from app.models.schemas import Citation, CodeChunk, ValidationResult


@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client."""
    return MagicMock()


@pytest.fixture
def answer_validator(mock_anthropic_client):
    """Create an AnswerValidator instance with mock client."""
    return AnswerValidator(
        anthropic_client=mock_anthropic_client,
        model="claude-3-5-sonnet-20241022",
    )


@pytest.fixture
def sample_chunks():
    """Create sample CodeChunk objects."""
    return [
        CodeChunk(
            id="chunk1",
            file="auth.py",
            language="python",
            start_line=10,
            end_line=30,
            type="function",
            content="def authenticate(user): ...",
        ),
        CodeChunk(
            id="chunk2",
            file="auth.py",
            language="python",
            start_line=35,
            end_line=50,
            type="function",
            content="def validate_token(token): ...",
        ),
    ]


@pytest.fixture
def sample_citations():
    """Create sample Citation objects."""
    return [
        Citation(
            file="auth.py",
            lines="10-30",
            relevance=0.95,
            preview="def authenticate(user): ...",
        ),
    ]


@pytest.mark.asyncio
async def test_validate_grounded_answer(answer_validator, mock_anthropic_client, sample_chunks, sample_citations):
    """Test validation of a well-grounded answer."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock()]
    mock_response.content[0].text = '''{
        "is_valid": true,
        "confidence": 0.95,
        "grounded": true,
        "hallucination_risk": "low",
        "missing_aspects": [],
        "suggestions": null
    }'''

    mock_anthropic_client.messages.create.return_value = mock_response

    validation = await answer_validator.validate_answer(
        query="How does authentication work?",
        answer="Authentication works by validating user credentials...",
        citations=sample_citations,
        retrieved_chunks=sample_chunks,
    )

    assert isinstance(validation, ValidationResult)
    assert validation.is_valid is True
    assert validation.confidence == 0.95
    assert validation.grounded is True
    assert validation.hallucination_risk == "low"


@pytest.mark.asyncio
async def test_validate_hallucinated_answer(answer_validator, mock_anthropic_client, sample_chunks, sample_citations):
    """Test validation detects hallucinations."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock()]
    mock_response.content[0].text = '''{
        "is_valid": false,
        "confidence": 0.3,
        "grounded": false,
        "hallucination_risk": "high",
        "missing_aspects": ["implementation details"],
        "suggestions": "The answer claims features not present in the code"
    }'''

    mock_anthropic_client.messages.create.return_value = mock_response

    validation = await answer_validator.validate_answer(
        query="How does authentication work?",
        answer="Authentication uses biometric scanning and blockchain...",
        citations=sample_citations,
        retrieved_chunks=sample_chunks,
    )

    assert validation.is_valid is False
    assert validation.confidence == 0.3
    assert validation.hallucination_risk == "high"
    assert len(validation.missing_aspects) > 0


@pytest.mark.asyncio
async def test_validate_answer_fallback_on_error(answer_validator, mock_anthropic_client, sample_chunks, sample_citations):
    """Test fallback behavior on validation error."""
    mock_anthropic_client.messages.create.side_effect = Exception("API error")

    validation = await answer_validator.validate_answer(
        query="Query",
        answer="Answer",
        citations=sample_citations,
        retrieved_chunks=sample_chunks,
    )

    assert isinstance(validation, ValidationResult)
    assert validation.confidence == 0.5
