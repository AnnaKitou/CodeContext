"""
Semantic code chunking using tree-sitter AST parsing.

Splits code into semantic units (functions, classes, methods) rather than
fixed-size chunks, preserving code structure and context.
"""

import importlib
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

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

    Supports Python, JavaScript, TypeScript, Go, Java, C/C++, C#, Rust, Ruby.
    Falls back to regex-based chunking when a parser is unavailable.
    """

    # Maps language name → (pip package module, exported function name)
    _LANG_SPECS: dict[str, tuple[str, str]] = {
        "python":     ("tree_sitter_python",    "language"),
        "javascript": ("tree_sitter_javascript", "language"),
        "typescript": ("tree_sitter_typescript", "language_typescript"),
        "tsx":        ("tree_sitter_typescript", "language_tsx"),
        "go":         ("tree_sitter_go",         "language"),
        "java":       ("tree_sitter_java",       "language"),
        "cpp":        ("tree_sitter_cpp",        "language"),
        "c":          ("tree_sitter_c",          "language"),
        "c_sharp":    ("tree_sitter_c_sharp",    "language"),
        "rust":       ("tree_sitter_rust",       "language"),
        "ruby":       ("tree_sitter_ruby",       "language"),
    }

    def __init__(self):
        """Initialize the chunker with tree-sitter."""
        self.parsers: dict[str, Parser] = {}
        self._init_parsers()

    def _init_parsers(self) -> None:
        """Initialize tree-sitter parsers for all supported languages."""
        ok, fail = [], []
        for lang_name, (module_name, func_name) in self._LANG_SPECS.items():
            try:
                mod = importlib.import_module(module_name)
                lang_fn = getattr(mod, func_name)
                language = Language(lang_fn())
                self.parsers[lang_name] = Parser(language)
                ok.append(lang_name)
            except Exception as e:
                fail.append(lang_name)
                logger.debug(f"Parser unavailable for {lang_name}: {e}")
        if ok:
            logger.info(f"Tree-sitter parsers ready: {', '.join(sorted(ok))}")
        if fail:
            logger.info(f"Regex fallback active for: {', '.join(sorted(fail))}")

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
        logger.debug(f"Chunking {file_path} ({language})")

        if language not in self.parsers:
            logger.debug(f"Parser not available for {language}, using fallback")
            return self._fallback_chunk(file_path, content, language)

        try:
            parser = self.parsers[language]
            tree = parser.parse(content.encode("utf-8"))
            root = tree.root_node
            return self._extract_definitions(
                file_path, content, language, root, root.child_count == 0
            )
        except Exception as e:
            logger.error(f"Tree-sitter parsing failed for {file_path}: {str(e)}")
            return self._fallback_chunk(file_path, content, language)

    def _extract_definitions(
        self,
        file_path: str,
        content: str,
        language: str,
        node: Any,
        is_root: bool = False,
    ) -> list[CodeChunk]:
        """Extract function and class definitions from AST node."""
        chunks = []
        lines = content.split("\n")
        definition_types = self._get_definition_types(language)

        for child in node.children:
            if child.type in definition_types:
                start_line = child.start_point[0] + 1
                end_line = child.end_point[0] + 1
                name = self._extract_name(child, lines)
                chunk_content = "\n".join(
                    lines[child.start_point[0] : child.end_point[0] + 1]
                )
                chunks.append(CodeChunk(
                    file=file_path,
                    language=language,
                    type=child.type,
                    name=name,
                    start_line=start_line,
                    end_line=end_line,
                    content=chunk_content,
                    metadata={"source": "tree_sitter", "node_type": child.type},
                ))

            nested = self._extract_definitions(file_path, content, language, child, False)
            chunks.extend(nested)

        return chunks

    @staticmethod
    def _get_definition_types(language: str) -> set[str]:
        """Get AST node types that represent definitions in a language."""
        definition_map: dict[str, set[str]] = {
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
                "arrow_function",
            },
            "typescript": {
                "function_declaration",
                "class_declaration",
                "method_definition",
                "function_expression",
                "arrow_function",
                "interface_declaration",
                "type_alias_declaration",
                "enum_declaration",
            },
            "tsx": {
                "function_declaration",
                "class_declaration",
                "method_definition",
                "function_expression",
                "arrow_function",
                "interface_declaration",
                "type_alias_declaration",
                "jsx_element",
            },
            "go": {
                "function_declaration",
                "method_declaration",
            },
            "java": {
                "method_declaration",
                "class_declaration",
                "constructor_declaration",
                "interface_declaration",
                "annotation_type_declaration",
            },
            "cpp": {
                "function_definition",
                "class_specifier",
                "struct_specifier",
            },
            "c": {
                "function_definition",
                "struct_specifier",
            },
            "c_sharp": {
                "method_declaration",
                "class_declaration",
                "interface_declaration",
                "constructor_declaration",
                "property_declaration",
            },
            "rust": {
                "function_item",
                "impl_item",
                "struct_item",
                "enum_item",
                "trait_item",
            },
            "ruby": {
                "method",
                "singleton_method",
                "class",
                "module",
            },
        }
        return definition_map.get(language, set())

    @staticmethod
    def _extract_name(node: Any, lines: list[str]) -> Optional[str]:
        """Extract the name of a function/class from AST node."""
        try:
            for child in node.children:
                if child.type == "identifier":
                    start = child.start_byte
                    end = child.end_byte
                    line_idx = child.start_point[0]
                    if line_idx < len(lines):
                        line = lines[line_idx]
                        return line[start : min(end, len(line))]
            return None
        except Exception:
            return None

    def _fallback_chunk(
        self, file_path: str, content: str, language: str
    ) -> list[CodeChunk]:
        """Fallback chunking via regex when tree-sitter parser is unavailable."""
        chunks: list[CodeChunk] = []
        lines = content.split("\n")

        if language == "python":
            for i, line in enumerate(lines):
                m = re.match(r"^\s*(def|class)\s+(\w+)", line)
                if m:
                    chunk_type = "function_definition" if m.group(1) == "def" else "class_definition"
                    name = m.group(2)
                    end_line = len(lines)
                    for j in range(i + 1, len(lines)):
                        if re.match(r"^\s*(def|class)\s+(\w+)", lines[j]):
                            end_line = j
                            break
                    chunks.append(CodeChunk(
                        file=file_path, language=language, type=chunk_type,
                        name=name, start_line=i + 1, end_line=end_line,
                        content="\n".join(lines[i:end_line]),
                        metadata={"source": "fallback_regex"},
                    ))

        elif language in ("javascript", "typescript", "tsx"):
            patterns = [
                (r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+(\w+)", "function_declaration"),
                (r"^\s*(?:export\s+)?(?:default\s+)?class\s+(\w+)", "class_declaration"),
                (r"^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(.*?\)\s*=>", "arrow_function"),
                (r"^\s*(?:export\s+)?interface\s+(\w+)", "interface_declaration"),
                (r"^\s*(?:export\s+)?enum\s+(\w+)", "enum_declaration"),
                (r"^\s*(?:export\s+)?type\s+(\w+)\s*=", "type_alias_declaration"),
                (r"^@\w+", "decorated_declaration"),
            ]
            i = 0
            while i < len(lines):
                line = lines[i]
                matched = False
                for pat, node_type in patterns:
                    m = re.match(pat, line)
                    if m:
                        name = m.group(1) if m.lastindex and m.lastindex >= 1 else None
                        brace_count = line.count("{") - line.count("}")
                        end = i + 1
                        if "{" in line:
                            for j in range(i + 1, len(lines)):
                                brace_count += lines[j].count("{") - lines[j].count("}")
                                if brace_count <= 0:
                                    end = j + 1
                                    break
                            else:
                                end = len(lines)
                        else:
                            end = min(i + 20, len(lines))
                        chunks.append(CodeChunk(
                            file=file_path, language=language, type=node_type,
                            name=name, start_line=i + 1, end_line=end,
                            content="\n".join(lines[i:end]),
                            metadata={"source": "fallback_regex"},
                        ))
                        i = end
                        matched = True
                        break
                if not matched:
                    i += 1

        elif language == "c_sharp":
            for i, line in enumerate(lines):
                m = re.match(
                    r"^\s*(?:public|private|protected|internal|static|async|override|virtual|abstract|\s)*"
                    r"(?:class|interface|void|string|int|bool|Task|IActionResult|ActionResult)\s+(\w+)",
                    line,
                )
                if m:
                    name = m.group(1)
                    brace_count = line.count("{") - line.count("}")
                    end_line = i + 1
                    for j in range(i + 1, len(lines)):
                        brace_count += lines[j].count("{") - lines[j].count("}")
                        if brace_count <= 0 and lines[j].strip():
                            end_line = j + 1
                            break
                    else:
                        end_line = len(lines)
                    chunks.append(CodeChunk(
                        file=file_path, language=language, type="method_declaration",
                        name=name, start_line=i + 1, end_line=end_line,
                        content="\n".join(lines[i:end_line]),
                        metadata={"source": "fallback_regex"},
                    ))

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
            ".tsx": "tsx",
            ".go": "go",
            ".java": "java",
            ".cpp": "cpp",
            ".cc": "cpp",
            ".cxx": "cpp",
            ".c": "c",
            ".cs": "c_sharp",
            ".rb": "ruby",
            ".rs": "rust",
            ".php": "php",
            ".kt": "kotlin",
            ".swift": "swift",
            ".scala": "scala",
        }
        for ext, lang in ext_to_lang.items():
            if file_path.endswith(ext):
                return lang
        return "unknown"


def is_code_file(file_path: str) -> bool:
    """Check if file is a code file we should chunk."""
    code_extensions = {
        ".py", ".js", ".ts", ".tsx", ".go", ".java",
        ".cpp", ".cc", ".cxx", ".c", ".rb", ".rs",
        ".cs", ".php", ".kt", ".swift", ".scala",
    }
    return any(file_path.endswith(ext) for ext in code_extensions)
