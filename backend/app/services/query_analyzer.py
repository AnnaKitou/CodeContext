"""Query analysis service for decomposing complex questions into sub-queries."""

import json
import logging
from typing import Any

from anthropic import Anthropic

from ..models.schemas import QueryDecomposition, SubQuery

logger = logging.getLogger(__name__)


class QueryAnalyzer:
    """
    Analyzes queries and decomposes complex questions into sub-queries.

    Uses Claude to understand query intent and determine if decomposition is needed.
    """

    def __init__(self, anthropic_client: Anthropic, model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize the QueryAnalyzer.

        Args:
            anthropic_client: Anthropic API client
            model: Claude model to use for analysis
        """
        self.client = anthropic_client
        self.model = model

    async def analyze_query(self, query: str) -> QueryDecomposition:
        """
        Analyze a query and decompose it if needed.

        Args:
            query: The user's natural language question

        Returns:
            QueryDecomposition with sub-queries if complex, or single query if simple
        """
        logger.info(f"Analyzing query: {query[:80]}...")

        try:
            prompt = self._build_analysis_prompt(query)
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = response.content[0].text
            decomposition_data = self._parse_response(response_text, query)

            logger.info(
                f"Query analysis complete. Complex: {decomposition_data['is_complex']}, "
                f"Sub-queries: {len(decomposition_data.get('sub_queries', []))}"
            )

            return QueryDecomposition(**decomposition_data)

        except Exception as e:
            logger.error(f"Query analysis failed: {str(e)}")
            return self._fallback_decomposition(query)

    def _build_analysis_prompt(self, query: str) -> str:
        """Build the prompt for query analysis."""
        return f"""Analyze this codebase question and determine if it needs decomposition.

Question: "{query}"

Respond with JSON (only JSON, no markdown):
{{
  "is_complex": boolean,
  "reasoning": "explanation of complexity",
  "sub_queries": [
    {{"question": "sub-question 1", "reasoning": "why needed", "priority": 1}},
    {{"question": "sub-question 2", "reasoning": "why needed", "priority": 2}}
  ],
  "estimated_depth": 1 or 2 or 3
}}

Rules:
- If query asks 1 thing: is_complex=false, no sub_queries
- If query asks 2+ things: is_complex=true, split into sub_queries
- Priority: 1=most important, 2=medium, 3=supporting
- estimated_depth: 1=simple retrieval, 2=iterative, 3=complex reasoning"""

    def _parse_response(self, response_text: str, original_query: str) -> dict[str, Any]:
        """Parse the Claude response into decomposition data."""
        try:
            data = json.loads(response_text)

            sub_queries = [
                SubQuery(
                    question=sq["question"],
                    reasoning=sq.get("reasoning", ""),
                    priority=sq.get("priority", 2),
                )
                for sq in data.get("sub_queries", [])
            ]

            return {
                "original_query": original_query,
                "is_complex": data.get("is_complex", False),
                "reasoning": data.get("reasoning", ""),
                "sub_queries": sub_queries,
                "estimated_depth": data.get("estimated_depth", 1),
            }

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse response JSON: {e}. Using fallback.")
            return self._parse_fallback(original_query)

    def _parse_fallback(self, query: str) -> dict[str, Any]:
        """Fallback parsing if JSON parsing fails."""
        is_complex = (
            len(query.split("?")) > 2
            or " and " in query.lower()
            or " and how " in query.lower()
        )

        sub_queries = []
        if is_complex:
            parts = query.split(" and ")
            for i, part in enumerate(parts):
                sub_queries.append(
                    SubQuery(
                        question=part.strip(),
                        reasoning="Separated from compound query",
                        priority=i + 1,
                    )
                )

        return {
            "original_query": query,
            "is_complex": is_complex,
            "reasoning": "Fallback decomposition based on heuristics",
            "sub_queries": sub_queries,
            "estimated_depth": 2 if is_complex else 1,
        }

    def _fallback_decomposition(self, query: str) -> QueryDecomposition:
        """Return a fallback decomposition if analysis fails."""
        logger.warning(f"Returning fallback decomposition for: {query[:80]}...")
        return QueryDecomposition(
            original_query=query,
            is_complex=False,
            reasoning="Analysis failed, treating as simple query",
            sub_queries=[],
            estimated_depth=1,
        )
