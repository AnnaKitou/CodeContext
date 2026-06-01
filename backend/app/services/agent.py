"""
LLM Agent: Orchestrates Claude API calls with RAG context and MCP tools.

Combines retrieved code chunks with live data from MCP (GitHub API)
to synthesize comprehensive answers with citations.
"""

import json
import logging
import requests

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
        self.model = "claude-opus-4-8"

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
            if not self.anthropic_client:
                raise ValueError("Anthropic client not initialized")

            # Build context from retrieved chunks
            context = self._build_context(retrieved_chunks)

            # Create system prompt
            system_prompt = """You are a helpful AI assistant that answers questions about codebases.
You have access to relevant code snippets that may help answer the user's question.

When answering:
1. Use the provided code snippets to inform your answer
2. Reference specific files and line numbers when citing code
3. Be clear about what code you're referencing
4. If you're unsure about something, say so

Format file references as: filename.py:line_number or filename.py:start_line-end_line"""

            # Prepare messages
            user_message = f"""Question: {query}

Here are relevant code snippets from the codebase:

{context}

Please answer the question based on the provided code context."""

            # Get API key from client
            api_key = self.anthropic_client.api_key

            # Call Claude API via direct HTTP request
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }

            payload = {
                "model": self.model,
                "max_tokens": 2048,
                "system": system_prompt,
                "messages": [
                    {"role": "user", "content": user_message},
                ],
            }

            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                json=payload,
                headers=headers,
            )

            # Extract answer from response
            answer_text = ""
            mcp_calls = []

            if response.status_code == 200:
                response_data = response.json()
                for block in response_data.get("content", []):
                    if block.get("type") == "text":
                        answer_text += block.get("text", "")
                    elif block.get("type") == "tool_use":
                        mcp_calls.append(block.get("name", ""))
            else:
                raise Exception(f"API error ({response.status_code}): {response.text}")

            # Extract citations from answer and context
            citations = self._extract_citations(answer_text, retrieved_chunks)

            return answer_text, citations, mcp_calls

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
        import re

        citations = []
        seen_files = set()

        # Pattern to match file:line references
        pattern = r"(\S+\.(?:py|js|ts|jsx|tsx|java|cpp|c|go|rs|rb|php))[:\s]*(\d+)?[-–]?(\d+)?"

        matches = re.finditer(pattern, answer, re.IGNORECASE)
        for match in matches:
            file_ref = match.group(1)
            start_line = int(match.group(2)) if match.group(2) else None
            end_line = int(match.group(3)) if match.group(3) else start_line

            # Look for matching chunk
            for chunk in retrieved_chunks:
                if file_ref in chunk.file or chunk.file.endswith(file_ref):
                    key = (chunk.file, chunk.start_line)
                    if key not in seen_files:
                        seen_files.add(key)
                        lines_str = (
                            f"{chunk.start_line}-{chunk.end_line}"
                            if chunk.start_line and chunk.end_line
                            else str(chunk.start_line)
                        )
                        citation = Citation(
                            file=chunk.file,
                            lines=lines_str,
                            relevance=chunk.relevance_score,
                            preview=chunk.content[:200] + "..."
                            if len(chunk.content) > 200
                            else chunk.content,
                        )
                        citations.append(citation)
                        break

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
