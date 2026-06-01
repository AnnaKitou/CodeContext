"""
LLM Agent: Orchestrates Claude API calls with RAG context and MCP tools.

Combines retrieved code chunks with live data from MCP (GitHub API)
to synthesize comprehensive answers with citations.
"""

import json
import logging

from app.models.schemas import Citation

logger = logging.getLogger(__name__)


class CodeContextAgent:
    """
    LLM-powered agent for answering questions about codebases.

    Uses Claude API with:
    - Retrieved code chunks as context
    - MCP tools for live GitHub data
    - Function calling for tool use
    """

    def __init__(self, anthropic_client=None, mcp_server=None):
        """
        Initialize the agent.

        Args:
            anthropic_client: Anthropic API client
            mcp_server: MCP server for GitHub integration
        """
        self.anthropic_client = anthropic_client
        self.mcp_server = mcp_server
        self.model = "claude-3-5-sonnet-20241022"

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
            use_mcp: Whether to use MCP tools

        Returns:
            Tuple of (answer, citations, mcp_calls_made)
        """
        logger.info(f"Agent answering query: {query[:100]}...")

        try:
            # TODO: Implement agent logic:
            # 1. Build context from retrieved_chunks
            # 2. Create system prompt with instructions for citations
            # 3. Define MCP tools if use_mcp=True:
            #    - get_file_blame
            #    - get_issue
            #    - get_pull_requests
            #    - get_commit_history
            # 4. Call Claude API with messages + tools
            # 5. Handle tool_calls if they occur (agentic loop)
            # 6. Extract citations from answer and context
            # 7. Return (answer, citations, tools_used)

            answer = "Feature not yet implemented."
            citations = []
            mcp_calls = []

            return answer, citations, mcp_calls

        except Exception as e:
            logger.error(f"Agent error: {str(e)}")
            raise

    def _build_context(self, chunks: list) -> str:
        """
        Build a context string from retrieved chunks.

        Args:
            chunks: List of RetrievedChunk objects

        Returns:
            Formatted context string for the prompt
        """
        context_parts = []

        for i, chunk in enumerate(chunks, 1):
            header = f"\n## Code Snippet {i} ({chunk.file}:{chunk.start_line}-{chunk.end_line})\n"
            context_parts.append(header)
            context_parts.append(f"```{chunk.language}\n{chunk.content}\n```\n")

        return "".join(context_parts)

    def _extract_citations(
        self, answer: str, retrieved_chunks: list
    ) -> list[Citation]:
        """
        Extract file/line citations from the answer and context.

        Args:
            answer: LLM-generated answer
            retrieved_chunks: Retrieved code chunks

        Returns:
            List of Citation objects
        """
        citations = []

        # TODO: Parse answer for file references
        # Look for patterns like "file.py:42" or "file.py (lines 40-50)"
        # Match with retrieved_chunks to create Citations

        return citations

    @staticmethod
    def _get_mcp_tools() -> list[dict]:
        """
        Define available MCP tools.

        Returns:
            List of tool definitions for Claude
        """
        return [
            {
                "name": "get_file_blame",
                "description": "Get git blame for a file (who last modified each line)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file",
                        },
                        "line_number": {
                            "type": "integer",
                            "description": "Optional: specific line number",
                        },
                    },
                    "required": ["file_path"],
                },
            },
            {
                "name": "get_issue",
                "description": "Get GitHub issue details",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "issue_number": {
                            "type": "integer",
                            "description": "GitHub issue number",
                        },
                    },
                    "required": ["issue_number"],
                },
            },
            {
                "name": "get_pull_requests",
                "description": "Search for pull requests by state, label, or keyword",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "state": {
                            "type": "string",
                            "enum": ["open", "closed", "all"],
                            "description": "PR state",
                        },
                        "keyword": {
                            "type": "string",
                            "description": "Search keyword",
                        },
                    },
                },
            },
            {
                "name": "get_commit_history",
                "description": "Get commit history for a file",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of commits to return",
                            "default": 10,
                        },
                    },
                    "required": ["file_path"],
                },
            },
        ]
