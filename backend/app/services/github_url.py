"""Parsing helpers for GitHub repository URLs."""

from urllib.parse import urlparse


def parse_owner_repo(repo_url: str | None) -> tuple[str | None, str | None]:
    """
    Extract (owner, repo_name) from a GitHub HTTPS URL.

    Args:
        repo_url: e.g. "https://github.com/owner/repo" or ".../repo.git"

    Returns:
        Tuple of (owner, repo_name), or (None, None) if it can't be parsed.
    """
    if not repo_url:
        return None, None

    try:
        parsed = urlparse(repo_url)
        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) >= 2:
            owner = path_parts[-2]
            name = path_parts[-1].removesuffix(".git")
            return owner, name
    except Exception:
        pass

    return None, None
