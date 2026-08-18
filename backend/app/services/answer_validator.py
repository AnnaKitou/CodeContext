"""Answer validation service for self-critique and quality assurance."""

import json
import logging
from typing import Any

from anthropic import Anthropic

from ..models.schemas import Citation, CodeChunk, ValidationResult

logger = logging.getLogger(__name__)


class AnswerValidator:
    """
    Validates answers by checking grounding and performing self-critique.

    Uses Claude to evaluate whether an answer is well-grounded in retrieved context
    and to identify potential hallucinations or missing aspects.
    """

    def __init__(self, anthropic_client: Anthropic, model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize the AnswerValidator.

        Args:
            anthropic_client: Anthropic API client
            model: Claude model to use for validation
        """
        self.client = anthropic_client
        self.model = model

    async def validate_answer(
        self,
        query: str,
        answer: str,
        citations: list[Citation],
        retrieved_chunks: list[CodeChunk],
    ) -> ValidationResult:
        """
        Validate an answer against retrieved context.

        Checks:
        1. Is the answer grounded in retrieved chunks?
        2. Are there unsupported claims (hallucinations)?
        3. What important aspects are missing?
        4. Overall confidence score

        Args:
            query: The original query
            answer: The generated answer
            citations: Citations provided with the answer
            retrieved_chunks: The retrieved code chunks used as context

        Returns:
            ValidationResult with validation details
        """
        logger.info(f"Validating answer for query: {query[:80]}...")

        try:
            prompt = self._build_validation_prompt(
                query=query,
                answer=answer,
                citations=citations,
                retrieved_chunks=retrieved_chunks,
            )

            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = response.content[0].text
            validation_data = self._parse_response(response_text)

            logger.info(
                f"Validation complete. Valid: {validation_data['is_valid']}, "
                f"Confidence: {validation_data['confidence']:.2f}"
            )

            return ValidationResult(**validation_data)

        except Exception as e:
            logger.error(f"Answer validation failed: {str(e)}")
            return self._fallback_validation()

    def _build_validation_prompt(
        self,
        query: str,
        answer: str,
        citations: list[Citation],
        retrieved_chunks: list[CodeChunk],
    ) -> str:
        """Build the prompt for answer validation."""
        context_text = self._format_context(retrieved_chunks)
        citations_text = self._format_citations(citations)

        return f"""You are a code review expert. Validate this answer against the provided context.

ORIGINAL QUERY: "{query}"

GENERATED ANSWER:
{answer}

PROVIDED CITATIONS:
{citations_text}

RETRIEVED CONTEXT (source of truth):
{context_text}

Perform a detailed self-critique. Respond with JSON (only JSON):
{{
  "is_valid": boolean,
  "confidence": number (0.0-1.0),
  "grounded": boolean,
  "hallucination_risk": "low" | "medium" | "high",
  "missing_aspects": ["aspect1", "aspect2"],
  "suggestions": "How to improve the answer"
}}

Evaluation criteria:
1. GROUNDED: Does answer only use info from context chunks?
2. HALLUCINATION: Are there claims not supported by context?
3. COMPLETE: Are all important aspects covered?
4. ACCURATE: Are citations correctly matched to claims?
5. CONFIDENCE: How confident should we be in this answer?

Be strict but fair. Flag any unsupported claims."""

    def _format_context(self, chunks: list[CodeChunk]) -> str:
        """Format retrieved chunks as readable context."""
        if not chunks:
            return "(No context retrieved)"

        formatted = []
        for chunk in chunks[:5]:
            formatted.append(f"File: {chunk.file} (lines {chunk.start_line}-{chunk.end_line})")
            formatted.append(f"Type: {chunk.type}")
            formatted.append(f"Content:\n{chunk.content[:300]}...\n")

        return "\n".join(formatted)

    def _format_citations(self, citations: list[Citation]) -> str:
        """Format citations for readability."""
        if not citations:
            return "(No citations)"

        formatted = []
        for i, citation in enumerate(citations, 1):
            formatted.append(
                f"{i}. {citation.file}:{citation.lines} "
                f"(relevance: {citation.relevance:.2f})"
            )

        return "\n".join(formatted)

    def _parse_response(self, response_text: str) -> dict[str, Any]:
        """Parse the Claude response into validation data."""
        try:
            # Try direct parsing first
            data = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from response text
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse validation response: {e}. Using fallback.")
                    return self._parse_fallback()
            else:
                logger.warning(f"No JSON found in response: {response_text[:100]}. Using fallback.")
                return self._parse_fallback()
        except ValueError as e:
            logger.warning(f"Failed to parse validation response: {e}. Using fallback.")
            return self._parse_fallback()

        try:
            return {
                "is_valid": data.get("is_valid", True),
                "confidence": float(data.get("confidence", 0.5)),
                "grounded": data.get("grounded", True),
                "hallucination_risk": data.get("hallucination_risk", "medium").lower(),
                "missing_aspects": data.get("missing_aspects", []),
                "suggestions": data.get("suggestions"),
            }
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to extract validation data: {e}. Using fallback.")
            return self._parse_fallback()

    def _parse_fallback(self) -> dict[str, Any]:
        """Fallback validation result if parsing fails."""
        return {
            "is_valid": True,
            "confidence": 0.5,
            "grounded": True,
            "hallucination_risk": "medium",
            "missing_aspects": [],
            "suggestions": "Validation inconclusive; check answer manually",
        }

    def _fallback_validation(self) -> ValidationResult:
        """Return a fallback validation result if validation fails."""
        logger.warning("Returning fallback validation result")
        return ValidationResult(
            is_valid=True,
            confidence=0.5,
            grounded=True,
            hallucination_risk="medium",
            missing_aspects=[],
            suggestions="Validation failed; check answer manually",
        )
