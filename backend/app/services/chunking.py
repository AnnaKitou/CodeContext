"""
Semantic code chunking using tree-sitter AST parsing.

Splits code into semantic units (functions, classes, methods) rather than
fixed-size chunks, preserving code structure and context.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

import tree_sitter
from tree_sitter import Language, Parser

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
    metadata: dict = field(default_factory=dict)


class SemanticChunker:
    """
    Chunks code files into semantic units using tree-sitter AST.

    Supports Python, JavaScript, TypeScript, Go, and other languages.
    """

    def __init__(self):
        """Initialize the chunker with tree-sitter."""
        self.parsers: dict[str, Parser] = {}
        self.languages = {
            "python": "python",
            "javascript": "javascript",
            "typescript": "typescript",
            "go": "go",
            "java": "java",
            "cpp": "cpp",
            "c": "c",
        }
        self._init_parsers()

    def _init_parsers(self) -> None:
        """Initialize tree-sitter parsers for supported languages."""
        for lang_name in self.languages.values():
            try:
                language = Language("tree_sitter_{}".format(lang_name), lang_name)
                parser = Parser()
                parser.set_language(language)
                self.parsers[lang_name] = parser
                logger.info(f"Initialized parser for {lang_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize parser for {lang_name}: {str(e)}")

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
        logger.info(f"Chunking {file_path} ({language})")
        chunks = []

        if language not in self.parsers:
            logger.warning(f"Parser not available for {language}, using fallback")
            return self._fallback_chunk(file_path, content, language)

        try:
            parser = self.parsers[language]
            tree = parser.parse(content.encode("utf-8"))
            root = tree.root_node

            # Extract semantic chunks from the AST
            chunks = self._extract_definitions(
                file_path, content, language, root, root.child_count == 0
            )

        except Exception as e:
            logger.error(f"Tree-sitter parsing failed for {file_path}: {str(e)}")
            chunks = self._fallback_chunk(file_path, content, language)

        return chunks

    def _extract_definitions(
        self,
        file_path: str,
        content: str,
        language: str,
        node: Any,
        is_root: bool = False,
    ) -> list[CodeChunk]:
        """
        Extract function and class definitions from AST node.

        Args:
            file_path: Path to the file
            content: File content
            language: Programming language
            node: AST node to process
            is_root: Whether this is the root node

        Returns:
            List of CodeChunk objects
        """
        chunks = []
        lines = content.split("\n")

        # Define patterns for different languages
        definition_types = self._get_definition_types(language)

        for child in node.children:
            if child.type in definition_types:
                start_line = child.start_point[0] + 1
                end_line = child.end_point[0] + 1

                # Extract name from the node
                name = self._extract_name(child, lines)

                # Get content
                chunk_content = "\n".join(
                    lines[child.start_point[0] : child.end_point[0] + 1]
                )

                chunk = CodeChunk(
                    file=file_path,
                    language=language,
                    type=child.type,
                    name=name,
                    start_line=start_line,
                    end_line=end_line,
                    content=chunk_content,
                    metadata={
                        "source": "tree_sitter",
                        "node_type": child.type,
                    },
                )
                chunks.append(chunk)

            # Recursively process children for nested definitions
            nested = self._extract_definitions(
                file_path, content, language, child, False
            )
            chunks.extend(nested)

        return chunks

    @staticmethod
    def _get_definition_types(language: str) -> set[str]:
        """Get AST node types that represent definitions in a language."""
        definition_map = {
            "python": {
                "function_definition",
                "class_definition",
                "decorated_definition",
            },
            "javascript": {
                "function_declaration",
                "class_declaration",
                "method_definition",
                "function_expression",
            },
            "typescript": {
                "function_declaration",
                "class_declaration",
                "method_definition",
                "function_expression",
                "interface_declaration",
            },
            "go": {
                "function_declaration",
                "method_declaration",
            },
            "java": {
                "method_declaration",
                "class_declaration",
            },
        }
        return definition_map.get(language, set())

    @staticmethod
    def _extract_name(node: Any, lines: list[str]) -> Optional[str]:
        """Extract the name of a function/class from AST node."""
        try:
            # Look for an identifier child
            for child in node.children:
                if child.type == "identifier":
                    start = child.start_byte
                    end = child.end_byte
                    line_idx = child.start_point[0]
                    if line_idx < len(lines):
                        line = lines[line_idx]
                        # Get text from the line
                        return line[start : min(end, len(line))]
            return None
        except Exception:
            return None

    def _fallback_chunk(
        self, file_path: str, content: str, language: str
    ) -> list[CodeChunk]:
        """
        Fallback chunking strategy when tree-sitter parsing fails.

        Uses regex-based detection of function/class definitions.
        """
        chunks = []
        lines = content.split("\n")

        if language == "python":
            import re

            for i, line in enumerate(lines):
                if re.match(r"^\s*(def|class)\s+(\w+)", line):
                    match = re.match(r"^\s*(def|class)\s+(\w+)", line)
                    if match:
                        chunk_type = "function_definition" if match.group(1) == "def" else "class_definition"
                        name = match.group(2)

                        # Find the end of the definition (next def/class or EOF)
                        end_line = i + 1
                        for j in range(i + 1, len(lines)):
                            if re.match(r"^\s*(def|class)\s+(\w+)", lines[j]):
                                end_line = j
                                break
                        else:
                            end_line = len(lines)

                        chunk_content = "\n".join(lines[i:end_line])
                        chunk = CodeChunk(
                            file=file_path,
                            language=language,
                            type=chunk_type,
                            name=name,
                            start_line=i + 1,
                            end_line=end_line,
                            content=chunk_content,
                            metadata={"source": "fallback_regex"},
                        )
                        chunks.append(chunk)

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
