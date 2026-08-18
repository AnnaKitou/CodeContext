"""Agent planning service for pre-execution strategy development."""

import json
import logging
from typing import Any

from anthropic import Anthropic

from ..models.schemas import QueryPlanResponse, QueryDecomposition, RetrievalStrategy

logger = logging.getLogger(__name__)


class AgentPlanner:
    """
    Plans agent actions before execution.

    Decides:
    - What data to retrieve
    - Which tools to use (MCP or standard)
    - Validation criteria
    - Reasoning approach (shallow/medium/deep)
    """

    def __init__(self, anthropic_client: Anthropic, model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize the AgentPlanner.

        Args:
            anthropic_client: Anthropic API client
            model: Claude model to use for planning
        """
        self.client = anthropic_client
        self.model = model

    async def plan_agent_actions(
        self,
        query: str,
        decomposition: QueryDecomposition,
        use_mcp: bool = True,
    ) -> QueryPlanResponse:
        """
        Plan how the agent should handle this query.

        Decides:
        - Single vs iterative retrieval
        - Which MCP tools to use
        - Validation strategy
        - Reasoning depth

        Args:
            query: Original query
            decomposition: Query decomposition from analyzer
            use_mcp: Whether MCP tools are available

        Returns:
            QueryPlanResponse with detailed action plan
        """
        logger.info(f"Planning agent actions for: {query[:80]}...")

        try:
            prompt = self._build_planning_prompt(
                query=query,
                decomposition=decomposition,
                use_mcp=use_mcp,
            )

            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = response.content[0].text
            plan_data = self._parse_response(response_text, query, decomposition)

            logger.info(
                f"Plan created. Strategy: {plan_data['retrieval_strategy'].retrieval_type}, "
                f"MCP tools: {len(plan_data['expected_tools'])}"
            )

            return QueryPlanResponse(**plan_data)

        except Exception as e:
            logger.error(f"Agent planning failed: {str(e)}")
            return self._fallback_plan(query, decomposition)

    def _build_planning_prompt(
        self,
        query: str,
        decomposition: QueryDecomposition,
        use_mcp: bool,
    ) -> str:
        """Build the prompt for agent planning."""
        complexity = "COMPLEX" if decomposition.is_complex else "SIMPLE"
        depth = decomposition.estimated_depth

        sub_queries_text = ""
        if decomposition.sub_queries:
            sub_queries_text = "\nSub-queries:\n"
            for sq in decomposition.sub_queries:
                sub_queries_text += (
                    f"- {sq.question} (priority: {sq.priority}, "
                    f"reasoning: {sq.reasoning})\n"
                )

        mcp_tools_available = (
            "get_file_blame, get_issue, get_pull_requests, get_commit_history"
            if use_mcp
            else "none"
        )

        return f"""You are an expert agent planner. Create an action plan for this query.

QUERY: "{query}"
COMPLEXITY: {complexity}
ESTIMATED DEPTH: {depth}/3{sub_queries_text}

AVAILABLE MCP TOOLS: {mcp_tools_available}
AVAILABLE DATA: ChromaDB code search, Git history, GitHub issues

Plan the agent's actions. Respond with JSON only:
{{
  "retrieval_strategy": {{
    "retrieval_type": "single_round" | "iterative",
    "use_mcp_tools": boolean,
    "mcp_tools_needed": ["tool1", "tool2"],
    "max_retrieval_rounds": 1 | 2 | 3,
    "top_k_per_round": 5 | 10
  }},
  "expected_tools": ["tool1", "tool2"],
  "reasoning": "Why this plan makes sense"
}}

Decision rules:
1. SIMPLE queries: single_round retrieval, no MCP
2. COMPLEX queries: iterative retrieval, consider MCP
3. DEPTH 1-2: max 2 retrieval rounds
4. DEPTH 3: up to 3 retrieval rounds
5. FILE BLAME/HISTORY: use get_file_blame, get_commit_history
6. ISSUES/PRs: use get_issue, get_pull_requests if mentioned
7. DEFAULT: prioritize speed (single_round) unless clearly need iteration"""

    def _parse_response(
        self,
        response_text: str,
        query: str,
        decomposition: QueryDecomposition,
    ) -> dict[str, Any]:
        """Parse the Claude response into plan data."""
        try:
            data = json.loads(response_text)

            strategy_data = data.get("retrieval_strategy", {})
            retrieval_strategy = RetrievalStrategy(
                retrieval_type=strategy_data.get("retrieval_type", "single_round"),
                use_mcp_tools=strategy_data.get("use_mcp_tools", False),
                mcp_tools_needed=strategy_data.get("mcp_tools_needed", []),
                max_retrieval_rounds=strategy_data.get("max_retrieval_rounds", 1),
                top_k_per_round=strategy_data.get("top_k_per_round", 5),
            )

            return {
                "query": query,
                "decomposition": decomposition,
                "retrieval_strategy": retrieval_strategy,
                "expected_tools": data.get("expected_tools", []),
                "reasoning": data.get("reasoning", ""),
            }

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse plan response: {e}. Using fallback.")
            return self._parse_fallback(query, decomposition)

    def _parse_fallback(
        self, query: str, decomposition: QueryDecomposition
    ) -> dict[str, Any]:
        """Fallback plan if parsing fails."""
        strategy = RetrievalStrategy(
            retrieval_type="iterative" if decomposition.is_complex else "single_round",
            max_retrieval_rounds=2 if decomposition.is_complex else 1,
        )

        return {
            "query": query,
            "decomposition": decomposition,
            "retrieval_strategy": strategy,
            "expected_tools": [],
            "reasoning": "Fallback plan based on query complexity heuristics",
        }

    def _fallback_plan(
        self,
        query: str,
        decomposition: QueryDecomposition,
    ) -> QueryPlanResponse:
        """Return a fallback plan if planning fails."""
        logger.warning(f"Returning fallback plan for: {query[:80]}...")

        strategy = RetrievalStrategy(
            retrieval_type="iterative" if decomposition.is_complex else "single_round",
            max_retrieval_rounds=2 if decomposition.is_complex else 1,
        )

        return QueryPlanResponse(
            query=query,
            decomposition=decomposition,
            retrieval_strategy=strategy,
            expected_tools=[],
            reasoning="Planning failed; using conservative fallback",
        )
