"""
Semantic code chunking using tree-sitter AST parsing.

Splits code into semantic units (functions, classes, methods) rather than
fixed-size chunks, preserving code structure and context.
"""

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CodeChunk:
    """Represents a semantic code chunk."""

    file: str
    language: str
    type: str  # "function", "class", "method", "module"
    name: str | None
    start_line: int
    end_line: int
    content: str
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SemanticChunker:
    """
    Chunks code files into semantic units using tree-sitter AST.

    Supports Python, JavaScript, TypeScript, Go, and other languages.
    """

    def __init__(self):
        """Initialize the chunker with tree-sitter."""
        # TODO: Initialize tree-sitter with language parsers
        # from tree_sitter import Language, Parser
        # self.parsers = {}
        # self.languages = ["python", "javascript", "go"]
        pass

    def chunk_file(self, file_path: str, content: str, language: str) -> list[CodeChunk]:
        """
        Chunk a single code file into semantic units.

        Args:
            file_path: Path to the file
            content: File content
            language: Programming language ("python", "javascript", etc.)

        Returns:
            List of CodeChunk objects
        """
        # TODO: Implement tree-sitter parsing
        # Steps:
        # 1. Parse AST using tree-sitter
        # 2. Identify top-level definitions (functions, classes)
        # 3. For each definition, extract start/end lines
        # 4. Create CodeChunk for each semantic unit
        # 5. Handle nested structures (classes with methods)

        logger.info(f"Chunking {file_path} ({language})")
        chunks = []

        # Placeholder
        return chunks

    def chunk_repository(
        self, repo_path: str, file_list: list[str]
    ) -> list[CodeChunk]:
        """
        Chunk an entire repository.

        Args:
            repo_path: Root path of repository
            file_list: List of file paths to chunk

        Returns:
            List of all CodeChunk objects
        """
        all_chunks = []

        for file_path in file_list:
            try:
                language = self._detect_language(file_path)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                chunks = self.chunk_file(file_path, content, language)
                all_chunks.extend(chunks)

            except Exception as e:
                logger.error(f"Failed to chunk {file_path}: {str(e)}")

        logger.info(f"Total chunks created: {len(all_chunks)}")
        return all_chunks

    @staticmethod
    def _detect_language(file_path: str) -> str:
        """Detect programming language from file extension."""
        ext_to_lang = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".go": "go",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
        }

        for ext, lang in ext_to_lang.items():
            if file_path.endswith(ext):
                return lang

        return "unknown"


def is_code_file(file_path: str) -> bool:
    """Check if file is a code file we should chunk."""
    code_extensions = {
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".go",
        ".java",
        ".cpp",
        ".c",
        ".rb",
        ".rs",
    }
    return any(file_path.endswith(ext) for ext in code_extensions)
