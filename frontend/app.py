"""
Gradio-based chat interface for CodeContext.

Uses manual Chatbot + Textbox layout for full compatibility with gr.Blocks + Tabs.
"""

import httpx
import logging

import gradio as gr

logger = logging.getLogger(__name__)

API_BASE_URL = "http://localhost:8000/api/v1"
client = httpx.Client()  # Will set timeout per-request


# ── Chat logic ────────────────────────────────────────────────────────────────

def chat(message: str, history: list, top_k: int, use_mcp: bool):
    """Send a message and return the updated history."""
    if not message.strip():
        return history, ""

    try:
        resp = client.post(
            f"{API_BASE_URL}/query",
            json={
                "query": message,
                "top_k": int(top_k),
                "use_mcp": use_mcp,
                "include_code_preview": True,
            },
            timeout=90.0,  # Query + Claude API call
        )

        if resp.status_code != 200:
            detail = resp.json().get("detail", "Unknown error")
            bot_reply = f"❌ Error: {detail}"
        else:
            data = resp.json()
            answer    = data.get("answer", "No answer")
            citations = data.get("citations", [])
            mcp_calls = data.get("mcp_calls", [])
            confidence = data.get("confidence", 0.0)

            lines = [f"{answer}\n"]

            if citations:
                lines.append("**📍 Citations:**")
                for i, c in enumerate(citations, 1):
                    ref = f"`{c['file']}:{c['lines']}`"
                    lines.append(f"{i}. {ref}  _(relevance: {c['relevance']:.0%})_")
                    if c.get("preview"):
                        lines.append(f"   > {c['preview'][:120]}…")

            if mcp_calls:
                lines.append(f"\n🔗 **Live data used:** {', '.join(mcp_calls)}")

            lines.append(f"\n🎯 **Confidence:** {confidence:.0%}")
            bot_reply = "\n".join(lines)

    except httpx.ConnectError:
        bot_reply = (
            "❌ Cannot connect to backend.  \n"
            "Make sure FastAPI is running:  \n"
            "`cd backend && fastapi dev app/main.py`"
        )
    except Exception as e:
        logger.error(f"Chat error: {e}")
        bot_reply = f"❌ Error: {e}"

    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": bot_reply},
    ]
    return history, ""


def clear_index() -> str:
    """Wipe all chunks from ChromaDB."""
    try:
        resp = client.delete(f"{API_BASE_URL}/ingest", timeout=30.0)
        if resp.status_code != 200:
            return f"❌ Failed to clear: {resp.json().get('detail', 'Unknown error')}"
        data = resp.json()
        return f"🗑 {data['message']}"
    except httpx.ConnectError:
        return "❌ Cannot connect to backend at http://localhost:8000"
    except Exception as e:
        return f"❌ Error: {e}"


def ingest(repo_url: str, repo_name: str, clear_first: bool) -> str:
    """Ingest a repository, optionally clearing the index first."""
    if not repo_url.strip() or not repo_name.strip():
        return "❌ Please provide both a repository URL and a name."

    try:
        resp = client.post(
            f"{API_BASE_URL}/ingest",
            json={
                "repository_url": repo_url,
                "repository_name": repo_name,
                "clear_before_ingest": clear_first,
            },
            timeout=600.0,  # Clone + chunk + index can take up to 10 minutes
        )
        if resp.status_code != 200:
            detail = resp.json().get("detail", "Unknown error")
            return f"❌ Ingestion failed: {detail}"

        data = resp.json()
        langs = ", ".join(data.get("languages", [])) or "—"
        prefix = "🔄 Old index wiped. " if clear_first else ""
        return (
            f"{prefix}✅ {data['message']}\n"
            f"• Files indexed : {data['files_indexed']}\n"
            f"• Chunks created: {data['chunks_created']}\n"
            f"• Languages     : {langs}"
        )
    except httpx.ConnectError:
        return "❌ Cannot connect to backend at http://localhost:8000"
    except Exception as e:
        return f"❌ Error: {e}"


# ── UI ────────────────────────────────────────────────────────────────────────

with gr.Blocks(title="CodeContext — Codebase Q&A") as demo:

    gr.Markdown(
        """
# 🔍 CodeContext
**RAG/MCP System for Codebase Understanding** — ask questions, get answers with source citations.
        """
    )

    with gr.Tabs():

        # ── Chat tab ──────────────────────────────────────────────────────────
        with gr.Tab("💬 Chat"):
            with gr.Row():

                # Left column: controls
                with gr.Column(scale=1, min_width=220):
                    gr.Markdown("### ⚙️ Settings")
                    top_k_slider = gr.Slider(
                        minimum=1, maximum=20, value=5, step=1,
                        label="Top-K Chunks",
                        info="Chunks retrieved per query",
                    )
                    use_mcp_cb = gr.Checkbox(
                        value=True,
                        label="Use MCP (GitHub)",
                        info="Enable live blame / PR / commit data",
                    )
                    gr.Markdown(
                        """
**Tips**
- Index a repo first (Ingest tab)
- Ask about functions, files, authors
- MCP needs `GITHUB_TOKEN` in `.env`
                        """
                    )

                # Right column: chatbot
                with gr.Column(scale=4):
                    chatbot = gr.Chatbot(
                        label="CodeContext",
                        height=460,
                    )
                    with gr.Row():
                        msg_box = gr.Textbox(
                            placeholder="Ask something about the codebase…",
                            label="",
                            scale=5,
                            lines=1,
                            autofocus=True,
                        )
                        send_btn = gr.Button("Send ➤", variant="primary", scale=1)
                    clear_btn = gr.Button("🗑 Clear chat", size="sm", variant="secondary")

            # Wire events
            send_btn.click(
                chat,
                inputs=[msg_box, chatbot, top_k_slider, use_mcp_cb],
                outputs=[chatbot, msg_box],
            )
            msg_box.submit(
                chat,
                inputs=[msg_box, chatbot, top_k_slider, use_mcp_cb],
                outputs=[chatbot, msg_box],
            )
            clear_btn.click(lambda: ([], ""), outputs=[chatbot, msg_box])

        # ── Ingest tab ────────────────────────────────────────────────────────
        with gr.Tab("📥 Ingest Repository"):
            gr.Markdown(
                "Clone a GitHub repository and index it so you can ask questions about it."
            )
            with gr.Row():
                with gr.Column():
                    repo_url_box = gr.Textbox(
                        label="Repository URL",
                        placeholder="https://github.com/tiangolo/fastapi",
                    )
                    repo_name_box = gr.Textbox(
                        label="Display name",
                        placeholder="fastapi",
                    )
                    clear_first_cb = gr.Checkbox(
                        value=False,
                        label="🔄 Replace existing index (wipe old data first)",
                        info="Turn this ON when indexing a new repo — otherwise old results will mix in.",
                    )
                    with gr.Row():
                        ingest_btn = gr.Button("🚀 Index repository", variant="primary", scale=3)
                        clear_idx_btn = gr.Button("🗑 Clear index", variant="secondary", scale=1)
                with gr.Column():
                    ingest_out = gr.Textbox(
                        label="Status", lines=8, interactive=False
                    )

            ingest_btn.click(
                ingest,
                inputs=[repo_url_box, repo_name_box, clear_first_cb],
                outputs=ingest_out,
            )
            clear_idx_btn.click(
                clear_index,
                outputs=ingest_out,
            )

        # ── About tab ─────────────────────────────────────────────────────────
        with gr.Tab("ℹ️ About"):
            gr.Markdown(
                """
## About CodeContext

A research project combining **RAG** + **MCP** for intelligent codebase Q&A.

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI |
| Vector DB | ChromaDB |
| Code parsing | tree-sitter (AST) |
| LLM | Anthropic API |
| Live data | GitHub API via MCP |
| Frontend | Gradio |

### Research Questions
1. Does AST-based chunking improve retrieval vs fixed-size?
2. How do RAG and MCP complement each other?
3. How reliable are the generated file/line citations?

---
Made by **Anna Kitou** · kitouanna@gmail.com
            """
            )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True,
        theme=gr.themes.Soft(),
    )
