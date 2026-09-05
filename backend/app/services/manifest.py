"""File-to-repository manifest for tracking indexed files and their source repos."""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class FileRepoManifest:
    """Manage a mapping of file paths to their source repository URLs.

    Also tracks the most recently ingested repo URL so consumers (e.g. the
    GitHub MCP server) can default to "whatever was just ingested" without
    needing a file path to look up.
    """

    def __init__(self, manifest_path: Path | str = "./chroma_db/file_repo_manifest.json"):
        """
        Initialize the manifest.

        Args:
            manifest_path: Path to store the manifest JSON file
        """
        self.manifest_path = Path(manifest_path)
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self._files: dict[str, str] = {}
        self._last_repo_url: Optional[str] = None
        self._load()

    def _load(self) -> None:
        """Load manifest from disk. Migrates the legacy flat-dict format transparently."""
        if not self.manifest_path.exists():
            self._files = {}
            self._last_repo_url = None
            return

        try:
            with open(self.manifest_path) as f:
                data = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load manifest: {e}")
            return

        if isinstance(data, dict) and "files" in data:
            self._files = data.get("files", {})
            self._last_repo_url = data.get("last_repo_url")
        else:
            # Legacy format: the whole object was the flat {file: repo_url} map.
            self._files = data if isinstance(data, dict) else {}
            self._last_repo_url = None

    def _save(self) -> None:
        """Save manifest to disk."""
        try:
            with open(self.manifest_path, "w") as f:
                json.dump({"files": self._files, "last_repo_url": self._last_repo_url}, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save manifest: {e}")

    def add_files(self, file_paths: list[str], repo_url: str) -> None:
        """
        Add file paths and associate them with a repository URL.

        Also records `repo_url` as the most recently ingested repo.

        Args:
            file_paths: List of file paths (relative or absolute)
            repo_url: GitHub repository URL
        """
        # Reload first: other instances (e.g. the query-side MCP server) may
        # have written to this same file since we last loaded it.
        self._load()
        for path in file_paths:
            # Normalize path: remove leading ./ or repo-specific prefixes
            normalized = self._normalize_path(path)
            self._files[normalized] = repo_url
        self._last_repo_url = repo_url
        self._save()
        logger.info(f"Added {len(file_paths)} files to manifest for {repo_url}")

    def get_repo_url(self, file_path: str) -> Optional[str]:
        """
        Look up the repository URL for a given file path.

        Args:
            file_path: File path to look up

        Returns:
            Repository URL if found, None otherwise
        """
        self._load()
        normalized = self._normalize_path(file_path)
        return self._files.get(normalized)

    def get_last_repo_url(self) -> Optional[str]:
        """Return the URL of the most recently ingested repository, if any."""
        self._load()
        return self._last_repo_url

    def _normalize_path(self, path: str) -> str:
        """Normalize a file path for lookup (remove leading slashes, backslashes, etc.)."""
        path = path.replace("\\", "/")
        prefixes = ("./", "temp_repos/", "temp_repos\\")
        changed = True
        while changed:
            changed = False
            for prefix in prefixes:
                stripped = path.removeprefix(prefix)
                if stripped != path:
                    path = stripped
                    changed = True
        return path

    def clear(self) -> None:
        """Clear all entries from the manifest, including the last-ingested repo."""
        self._files.clear()
        self._last_repo_url = None
        self._save()
        logger.info("Manifest cleared")
