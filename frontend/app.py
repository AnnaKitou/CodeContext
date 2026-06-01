"""
Gradio-based chat interface for CodeContext.

Provides a user-friendly way to ask questions about indexed codebases
with interactive citation viewing and source code highlighting.
"""

import asyncio
import httpx
import logging
from typing import AsyncGenerator

import gradio as gr

logger = logging.getLogger(__name__)

# Backend API URL
API_BASE_URL = "http://localhost:8000/api/v1"


class CodeContextChat:
    """Gradio chat interface for CodeContext."""

    def __init__(self, api_base_url: str = API_BASE_URL):
        """Initialize the chat interface."""
        self.api_base_url = api_base_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def chat(
        self,
        message: str,
        history: list,
        top_k: int = 5,
        use_mcp: bool = True,
    ) -> str:
        """
        Process a user message and return the assistant response.

        Args:
            message: User's question
            history: Chat history (unused in this implementation)
            top_k: Number of code chunks to retrieve
            use_mcp: Whether to use MCP tools

        Returns:
            Formatted response with citations
        """
        if not message.strip():
            return "Please ask a question."

        try:
            # Call the backend API
            response = await self.client.post(
                f"{self.api_base_url}/query",
                json={
                    "query": message,
                    "top_k": top_k,
                    "use_mcp": use_mcp,
                    "include_code_preview": True,
                },
            )

            if response.status_code != 200:
                error_detail = response.json().get("detail", "Unknown error")
                return f"Error: {error_detail}"

            data = response.json()

            # Format response with citations
            answer = data.get("answer", "No answer")
            citations = data.get("citations", [])
            mcp_calls = data.get("mcp_calls", [])
            confidence = data.get("confidence", 0.0)

            # Build formatted output
            output = f"**Answer:** {answer}\n\n"

            if citations:
                output += "**Citations:**\n"
                for i, citation in enumerate(citations, 1):
                    file_ref = f"{citation['file']}:{citation['lines']}"
                    relevance = f"{citation['relevance']:.2%}"
                    output += f"{i}. [{file_ref}]({file_ref}) (relevance: {relevance})\n"

            if citation.get("preview"):
                output += f"\n**Preview:** {citation.get('preview')}\n"

            if mcp_calls:
                output += f"\n**Live Data Used:** {', '.join(mcp_calls)}\n"

            output += f"\n**Confidence:** {confidence:.2%}"

            return output

        except httpx.ConnectError:
            return (
                "❌ Cannot connect to backend. "
                "Make sure FastAPI is running at http://localhost:8000"
            )
        except Exception as e:
            logger.error(f"Chat error: {str(e)}")
            return f"Error: {str(e)}"

    async def ingest_repository(self, repo_url: str, repo_name: str) -> str:
        """
        Ingest a repository for indexing.

        Args:
            repo_url: GitHub repository URL
            repo_name: Repository name

        Returns:
            Status message
        """
        try:
            response = await self.client.post(
                f"{self.api_base_url}/ingest",
                json={
                    "repository_url": repo_url,
                    "repository_name": repo_name,
                },
            )

            if response.status_code != 200:
                error_detail = response.json().get("detail", "Unknown error")
                return f"❌ Ingestion failed: {error_detail}"

            data = response.json()
            return (
                f"✅ {data['message']}\n"
                f"Files indexed: {data['files_indexed']}\n"
                f"Chunks created: {data['chunks_created']}\n"
                f"Languages: {', '.join(data['languages'])}"
            )

        except httpx.ConnectError:
            return (
                "❌ Cannot connect to backend. "
                "Make sure FastAPI is running at http://localhost:8000"
            )
        except Exception as e:
            logger.error(f"Ingest error: {str(e)}")
            return f"❌ Error: {str(e)}"


def create_interface() -> gr.Blocks:
    """Create the Gradio interface."""
    chat = CodeContextChat()

    with gr.Blocks(title="CodeContext - Codebase Q&A") as demo:
        gr.Markdown(
            """
# 🔍 CodeContext
**RAG/MCP System for Codebase Understanding**

Ask questions about any indexed codebase and get answers with precise source code citations.
            """
        )

        with gr.Tabs():
            # Chat Tab
            with gr.Tab("💬 Chat"):
                gr.Markdown("Ask questions about the indexed codebase.")

                with gr.Row():
                    with gr.Column():
                        top_k = gr.Slider(
                            minimum=1,
                            maximum=20,
                            value=5,
                            step=1,
                            label="Top-K Chunks",
                            info="Number of code chunks to retrieve",
                        )
                        use_mcp = gr.Checkbox(
                            value=True,
                            label="Use MCP",
                            info="Enable live GitHub data (blame, commits, issues)",
                        )

                with gr.Group():
                    chatbot = gr.ChatInterface(
                        chat.chat,
                        additional_inputs=[top_k, use_mcp],
                        examples=[
                            "What does the main function do?",
                            "How is authentication implemented?",
                            "What are the API endpoints?",
                            "Explain the database schema.",
                            "Who recently modified the payment processor?",
                        ],
                    )

            # Ingest Tab
            with gr.Tab("📥 Ingest Repository"):
                gr.Markdown("Index a new repository for semantic search.")

                with gr.Group():
                    repo_url = gr.Textbox(
                        label="Repository URL",
                        placeholder="https://github.com/user/repo",
                        info="GitHub repository URL to index",
                    )
                    repo_name = gr.Textbox(
                        label="Repository Name",
                        placeholder="my-project",
                        info="Display name for the repository",
                    )
                    ingest_btn = gr.Button("🚀 Start Ingestion", variant="primary")
                    ingest_output = gr.Textbox(
                        label="Status",
                        interactive=False,
                        lines=5,
                    )

                    ingest_btn.click(
                        chat.ingest_repository,
                        inputs=[repo_url, repo_name],
                        outputs=ingest_output,
                    )

            # About Tab
            with gr.Tab("ℹ️ About"):
                gr.Markdown(
                    """
## About CodeContext

**CodeContext** is a research project combining:
- **RAG (Retrieval-Augmented Generation)**: Semantic code chunking with tree-sitter
- **MCP (Model Context Protocol)**: Live GitHub API integration
- **LLM Agent**: Claude API with function calling

### Features
- 🔍 Semantic search across codebases
- 📍 Precise source code citations (file/line)
- 🔗 Live GitHub integration (blame, commits, PRs)
- 💡 Context-aware answers

### Research Questions
- Does AST-based chunking improve retrieval quality?
- How do RAG and MCP patterns complement each other?
- How reliable are the generated citations?

### Stack
- Backend: FastAPI, ChromaDB, tree-sitter
- Frontend: Gradio
- LLM: Claude API (Anthropic)
- Code Analysis: tree-sitter AST parsing
- MCP: GitHub API integration

### Try It
1. **Ingest** a repository (GitHub)
2. **Ask** questions about the code
3. **View** citations and source code
4. **Explore** with live GitHub data

---

Made by [Anna Kitou](mailto:a.kitou@codehub.gr)
                    """
                )

    return demo


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    demo = create_interface()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True,
        share=False,
    )
