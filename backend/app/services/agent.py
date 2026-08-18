"""
LLM Agent: Orchestrates Claude API calls with RAG context and MCP tools.

Combines retrieved code chunks with live data from MCP (GitHub API)
to synthesize comprehensive answers with citations.

Enhanced with agentic reasoning: query decomposition, adaptive retrieval,
answer validation, and multi-step reasoning chains (ReAct pattern).
"""

import json
import logging
import re
from datetime import datetime, timezone

from ..models.schemas import Citation, ThinkingStep, QueryResponseV2

logger = logging.getLogger(__name__)


class CodeContextAgent:
    """
    LLM-powered agent for answering questions about codebases.

    Uses Claude API with:
    - Retrieved code chunks as context
    - MCP tools for live GitHub data (when mcp_server is provided)
    - Tool-use agentic loop for multi-step reasoning
    """

    def __init__(
        self,
        anthropic_client=None,
        mcp_server=None,
        model: str = "claude-sonnet-4-6",
        query_analyzer=None,
        agent_planner=None,
        adaptive_retriever=None,
        answer_validator=None,
    ):
        """
        Initialize the agent.

        Args:
            anthropic_client: Anthropic SDK client instance
            mcp_server: MCPGithubServer for live GitHub data (optional)
            model: Claude model to use
            query_analyzer: QueryAnalyzer for query decomposition (optional)
            agent_planner: AgentPlanner for action planning (optional)
            adaptive_retriever: AdaptiveRetriever for multi-step retrieval (optional)
            answer_validator: AnswerValidator for self-critique (optional)
        """
        self.anthropic_client = anthropic_client
        self.mcp_server = mcp_server
        self.model = model
        self.query_analyzer = query_analyzer
        self.agent_planner = agent_planner
        self.adaptive_retriever = adaptive_retriever
        self.answer_validator = answer_validator
        self.thinking_steps: list[ThinkingStep] = []

    async def answer(
        self,
        query: str,
        retrieved_chunks: list,
        use_mcp: bool = True,
    ) -> tuple[str, list[Citation], list[str]]:
        """
        Generate an answer using Claude with retrieved context.

        Args:
            query: User's question
            retrieved_chunks: Code chunks from RAG retriever
            use_mcp: Whether to use MCP tools for live GitHub data

        Returns:
            Tuple of (answer_text, citations, mcp_calls_made)
        """
        logger.info(f"Agent answering query: {query[:100]}...")

        if not self.anthropic_client:
            raise ValueError("Anthropic client not initialized")

        context = self._build_context(retrieved_chunks)

        system_prompt = (
            "You are a helpful AI assistant that answers questions about codebases.\n"
            "You have access to relevant code snippets that may help answer the user's question.\n\n"
            "When answering:\n"
            "1. Use the provided code snippets to inform your answer\n"
            "2. Reference specific files and line numbers when citing code "
            "(format: filename.py:line_number or filename.py:start-end)\n"
            "3. Be clear and concise about what code you're referencing\n"
            "4. If you're unsure about something, say so"
        )

        user_message = (
            f"Question: {query}\n\n"
            f"Here are relevant code snippets from the codebase:\n\n"
            f"{context}\n\n"
            "Please answer the question based on the provided code context."
        )

        mcp_calls: list[str] = []
        tools = self._get_mcp_tools() if (use_mcp and self.mcp_server) else []

        messages: list[dict] = [{"role": "user", "content": user_message}]

        kwargs: dict = {
            "model": self.model,
            "max_tokens": 2048,
            "system": system_prompt,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        response = self.anthropic_client.messages.create(**kwargs)

        # Agentic tool-use loop
        while response.stop_reason == "tool_use" and self.mcp_server:
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    mcp_calls.append(block.name)
                    logger.info(f"Calling MCP tool: {block.name}")
                    try:
                        result = await self.mcp_server.execute_tool(block.name, **block.input)
                    except Exception as e:
                        result = {"error": str(e)}
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    })

            messages.append({"role": "assistant", "content": list(response.content)})
            messages.append({"role": "user", "content": tool_results})
            kwargs["messages"] = messages
            response = self.anthropic_client.messages.create(**kwargs)

        # Extract final text answer
        answer_text = ""
        for block in response.content:
            if block.type == "text":
                answer_text += block.text

        citations = self._extract_citations(answer_text, retrieved_chunks)
        return answer_text, citations, mcp_calls

    def _build_context(self, chunks: list) -> str:
        """Build a formatted context string from retrieved code chunks."""
        parts = []
        for i, chunk in enumerate(chunks, 1):
            parts.append(
                f"\n## Code Snippet {i} ({chunk.file}:{chunk.start_line}-{chunk.end_line})\n"
                f"```{chunk.language}\n{chunk.content}\n```\n"
            )
        return "".join(parts)

    def _extract_citations(
        self, answer: str, retrieved_chunks: list
    ) -> list[Citation]:
        """Extract file/line citations from the LLM answer and retrieved chunks."""
        citations: list[Citation] = []
        seen: set[tuple] = set()

        pattern = r"(\S+\.(?:py|js|ts|jsx|tsx|java|cpp|c|cs|go|rs|rb|php))[:\s]*(\d+)?[-–]?(\d+)?"
        for match in re.finditer(pattern, answer, re.IGNORECASE):
            file_ref = match.group(1)
            for chunk in retrieved_chunks:
                if file_ref in chunk.file or chunk.file.endswith(file_ref):
                    key = (chunk.file, chunk.start_line)
                    if key not in seen:
                        seen.add(key)
                        lines_str = (
                            f"{chunk.start_line}-{chunk.end_line}"
                            if chunk.start_line and chunk.end_line
                            else str(chunk.start_line)
                        )
                        citations.append(Citation(
                            file=chunk.file,
                            lines=lines_str,
                            relevance=chunk.relevance_score,
                            preview=(
                                chunk.content[:200] + "..."
                                if len(chunk.content) > 200
                                else chunk.content
                            ),
                        ))
                    break

        return citations

    async def answer_with_reasoning(
        self,
        query: str,
        use_mcp: bool = True,
        enable_critique: bool = True,
    ) -> QueryResponseV2:
        """
        Generate an answer using agentic reasoning (ReAct pattern).

        Full reasoning chain:
        1. PLAN: Analyze query, decompose if complex
        2. PLAN: Decide retrieval strategy and tools needed
        3. RETRIEVE: Execute adaptive (possibly multi-step) retrieval
        4. REASON: Call Claude with retrieved context
        5. CRITIQUE: Validate answer against context (optional)
        6. REFLECT: Compile thinking steps and confidence

        Args:
            query: User's question
            use_mcp: Whether to use MCP tools
            enable_critique: Whether to run self-critique validation

        Returns:
            QueryResponseV2 with answer, citations, and visible reasoning
        """
        import time
        start_time = time.time()

        logger.info(f"Starting agentic reasoning for: {query[:100]}...")
        self.thinking_steps = []

        try:
            self._add_thinking_step(
                "plan",
                f"Received query: {query[:100]}...",
            )

            decomposition = await self._plan_phase(query)
            plan = await self._plan_strategy(query, decomposition, use_mcp)

            retrieved_chunks, queries_used, retrieval_rounds = await self._retrieve_phase(
                query=query,
                plan=plan,
            )

            answer_text, citations, mcp_calls = await self._reason_phase(
                query=query,
                retrieved_chunks=retrieved_chunks,
                use_mcp=use_mcp,
            )

            validation = None
            if enable_critique and self.answer_validator:
                validation = await self._critique_phase(
                    query=query,
                    answer=answer_text,
                    citations=citations,
                    retrieved_chunks=retrieved_chunks,
                )

            processing_time_ms = (time.time() - start_time) * 1000

            self._add_thinking_step(
                "reflect",
                f"Reasoning complete. Retrieved {len(retrieved_chunks)} chunks, "
                f"validated answer quality.",
                confidence=0.9,
            )

            return QueryResponseV2(
                answer=answer_text,
                citations=citations,
                mcp_calls=mcp_calls,
                confidence=self._compute_confidence(retrieved_chunks, validation),
                processing_time_ms=processing_time_ms,
                thinking_process=self.thinking_steps,
                query_decomposition=decomposition,
                validation=validation,
                retrieval_rounds=retrieval_rounds,
                num_retrieval_queries=len(queries_used),
            )

        except Exception as e:
            logger.error(f"Agentic reasoning failed: {str(e)}", exc_info=True)
            return self._fallback_response(query)

    async def _plan_phase(self, query: str):
        """Analyze and decompose the query."""
        self._add_thinking_step(
            "plan",
            "Analyzing query complexity and intent...",
        )

        if not self.query_analyzer:
            return None

        decomposition = await self.query_analyzer.analyze_query(query)
        self._add_thinking_step(
            "decompose",
            f"Query complexity: {'COMPLEX' if decomposition.is_complex else 'SIMPLE'}. "
            f"Sub-queries: {len(decomposition.sub_queries)}",
            confidence=0.95,
        )
        return decomposition

    async def _plan_strategy(self, query: str, decomposition, use_mcp: bool):
        """Plan agent actions."""
        if not self.agent_planner or not decomposition:
            return None

        self._add_thinking_step(
            "plan",
            "Planning retrieval strategy and tools...",
        )

        plan = await self.agent_planner.plan_agent_actions(
            query=query,
            decomposition=decomposition,
            use_mcp=use_mcp,
        )

        self._add_thinking_step(
            "plan",
            f"Strategy: {plan.retrieval_strategy.retrieval_type} retrieval, "
            f"max {plan.retrieval_strategy.max_retrieval_rounds} rounds. "
            f"Tools: {plan.expected_tools or 'none'}",
            confidence=0.9,
        )
        return plan

    async def _retrieve_phase(self, query: str, plan):
        """Execute adaptive retrieval."""
        self._add_thinking_step(
            "retrieve",
            "Executing retrieval strategy...",
        )

        if not self.adaptive_retriever:
            return [], [], 0

        strategy = plan.retrieval_strategy if plan else None
        if not strategy:
            strategy = None

        retrieved_chunks, queries_used, retrieval_rounds = await self.adaptive_retriever.retrieve_with_refinement(
            query=query,
            enable_iterative=strategy and strategy.retrieval_type == "iterative",
        )

        self._add_thinking_step(
            "retrieve",
            f"Retrieved {len(retrieved_chunks)} chunks over {retrieval_rounds} round(s). "
            f"Queries used: {len(queries_used)}",
            results_found=len(retrieved_chunks),
            confidence=min(1.0, len(retrieved_chunks) / 10),
        )

        return retrieved_chunks, queries_used, retrieval_rounds

    async def _reason_phase(self, query: str, retrieved_chunks: list, use_mcp: bool):
        """Generate answer using Claude."""
        self._add_thinking_step(
            "reason",
            "Synthesizing answer from context...",
        )

        answer_text, citations, mcp_calls = await self.answer(
            query=query,
            retrieved_chunks=retrieved_chunks,
            use_mcp=use_mcp,
        )

        self._add_thinking_step(
            "reason",
            f"Answer generated with {len(citations)} citations. "
            f"MCP calls: {len(mcp_calls)}",
            confidence=0.85,
        )

        return answer_text, citations, mcp_calls

    async def _critique_phase(self, query: str, answer: str, citations: list, retrieved_chunks: list):
        """Validate answer with self-critique."""
        self._add_thinking_step(
            "critique",
            "Performing self-critique on answer quality...",
        )

        validation = await self.answer_validator.validate_answer(
            query=query,
            answer=answer,
            citations=citations,
            retrieved_chunks=retrieved_chunks,
        )

        risk_level = validation.hallucination_risk
        self._add_thinking_step(
            "critique",
            f"Validation: {'VALID' if validation.is_valid else 'INVALID'}. "
            f"Grounding: {'YES' if validation.grounded else 'NO'}. "
            f"Hallucination risk: {risk_level}",
            confidence=validation.confidence,
        )

        return validation

    def _add_thinking_step(
        self,
        step_type: str,
        content: str,
        queries_used: list[str] | None = None,
        results_found: int | None = None,
        confidence: float | None = None,
    ) -> None:
        """Add a thinking step to the reasoning chain."""
        step = ThinkingStep(
            step_type=step_type,
            content=content,
            queries_used=queries_used,
            results_found=results_found,
            confidence=confidence,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.thinking_steps.append(step)
        logger.debug(f"[{step_type}] {content}")

    def _compute_confidence(self, retrieved_chunks: list, validation=None) -> float:
        """Compute overall confidence score."""
        base_confidence = min(1.0, len(retrieved_chunks) / 10 * 0.8 + 0.1)

        if validation:
            base_confidence = base_confidence * 0.5 + validation.confidence * 0.5

        return min(1.0, base_confidence)

    def _fallback_response(self, query: str) -> QueryResponseV2:
        """Return a fallback response if reasoning fails."""
        logger.warning(f"Returning fallback response for: {query[:80]}...")

        self._add_thinking_step(
            "reflect",
            "Reasoning failed; returning fallback response",
            confidence=0.3,
        )

        return QueryResponseV2(
            answer="An error occurred while processing your query. Please try again.",
            citations=[],
            mcp_calls=[],
            confidence=0.0,
            processing_time_ms=0,
            thinking_process=self.thinking_steps,
            query_decomposition=None,
            validation=None,
            retrieval_rounds=0,
            num_retrieval_queries=0,
        )

    @staticmethod
    def _get_mcp_tools() -> list[dict]:
        """Tool definitions exposed to Claude for GitHub MCP calls."""
        return [
            {
                "name": "get_file_blame",
                "description": "Get git blame for a file (who last modified each line)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to the file"},
                        "line_number": {"type": "integer", "description": "Optional specific line"},
                    },
                    "required": ["file_path"],
                },
            },
            {
                "name": "get_issue",
                "description": "Get GitHub issue details by issue number",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "issue_number": {"type": "integer", "description": "GitHub issue number"},
                    },
                    "required": ["issue_number"],
                },
            },
            {
                "name": "get_pull_requests",
                "description": "Search for pull requests by state or keyword",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "state": {"type": "string", "enum": ["open", "closed", "all"]},
                        "keyword": {"type": "string", "description": "Search keyword in title/body"},
                    },
                },
            },
            {
                "name": "get_commit_history",
                "description": "Get recent commit history for a specific file",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to the file"},
                        "limit": {"type": "integer", "description": "Number of commits (default 10)"},
                    },
                    "required": ["file_path"],
                },
            },
        ]
