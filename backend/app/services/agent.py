"""
LLM Agent: Orchestrates Claude API calls with RAG context and MCP tools.

Combines retrieved code chunks with live data from MCP (GitHub API)
to synthesize comprehensive answers with citations.
"""

import json
import logging
import re

from app.models.schemas import Citation

logger = logging.getLogger(__name__)


class CodeContextAgent:
    """
    LLM-powered agent for answering questions about codebases.

    Uses Claude API with:
    - Retrieved code chunks as context
    - MCP tools for live GitHub data (when mcp_server is provided)
    - Tool-use agentic loop for multi-step reasoning
    """

    def __init__(self, anthropic_client=None, mcp_server=None, model: str = "claude-sonnet-4-6"):
        """
        Initialize the agent.

        Args:
            anthropic_client: Anthropic SDK client instance
            mcp_server: MCPGithubServer for live GitHub data (optional)
            model: Claude model to use
        """
        self.anthropic_client = anthropic_client
        self.mcp_server = mcp_server
        self.model = model

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
