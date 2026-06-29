"""File-to-repository manifest for tracking indexed files and their source repos."""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class FileRepoManifest:
    """Manage a mapping of file paths to their source repository URLs."""

    def __init__(self, manifest_path: Path | str = "./chroma_db/file_repo_manifest.json"):
        """
        Initialize the manifest.

        Args:
            manifest_path: Path to store the manifest JSON file
        """
        self.manifest_path = Path(manifest_path)
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict[str, str]:
        """Load manifest from disk, or return empty dict if not found."""
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load manifest: {e}")
        return {}

    def _save(self) -> None:
        """Save manifest to disk."""
        try:
            with open(self.manifest_path, "w") as f:
                json.dump(self._data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save manifest: {e}")

    def add_files(self, file_paths: list[str], repo_url: str) -> None:
        """
        Add file paths and associate them with a repository URL.

        Args:
            file_paths: List of file paths (relative or absolute)
            repo_url: GitHub repository URL
        """
        for path in file_paths:
            # Normalize path: remove leading ./ or repo-specific prefixes
            normalized = self._normalize_path(path)
            self._data[normalized] = repo_url
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
        normalized = self._normalize_path(file_path)
        return self._data.get(normalized)

    def _normalize_path(self, path: str) -> str:
        """Normalize a file path for lookup (remove leading slashes, backslashes, etc.)."""
        path = path.replace("\\", "/")
        while path.startswith(("./", "temp_repos/", "temp_repos\\")):
            path = path.lstrip("./").lstrip("temp_repos/").lstrip("temp_repos\\")
        return path

    def clear(self) -> None:
        """Clear all entries from the manifest."""
        self._data.clear()
        self._save()
        logger.info("Manifest cleared")
