"""Tests for MCPGithubServer's dynamic default-repo resolution."""

from unittest.mock import MagicMock, patch

import pytest

from app.core.config import settings
from app.services.manifest import FileRepoManifest
from app.services.mcp_server import MCPGithubServer


@pytest.fixture(autouse=True)
def _isolated_chroma_path(tmp_path, monkeypatch):
    """Point settings.CHROMA_DB_PATH at a per-test temp dir.

    MCPGithubServer builds its own FileRepoManifest from settings.CHROMA_DB_PATH
    internally, so tests need this redirected before constructing the server.
    """
    monkeypatch.setattr(settings, "CHROMA_DB_PATH", str(tmp_path))
    yield tmp_path


def _manifest_path(chroma_path) -> str:
    return f"{chroma_path}/file_repo_manifest.json"


@patch("app.services.mcp_server.Github")
def test_repo_property_uses_manifest_last_repo_when_present(mock_github_cls, _isolated_chroma_path):
    manifest = FileRepoManifest(_manifest_path(_isolated_chroma_path))
    manifest.add_files(["a.py"], "https://github.com/foo/bar")

    mock_client = mock_github_cls.return_value
    mock_repo = MagicMock()
    mock_client.get_repo.return_value = mock_repo

    server = MCPGithubServer(github_token="tok")

    assert server.repo is mock_repo
    mock_client.get_repo.assert_called_once_with("foo/bar")


@patch("app.services.mcp_server.Github")
def test_repo_property_falls_back_to_static_settings_when_manifest_empty(
    mock_github_cls, _isolated_chroma_path
):
    mock_client = mock_github_cls.return_value
    mock_repo = MagicMock()
    mock_client.get_repo.return_value = mock_repo

    server = MCPGithubServer(github_token="tok", repo_owner="seed", repo_name="repo")

    assert server.repo is mock_repo
    mock_client.get_repo.assert_called_once_with("seed/repo")


@patch("app.services.mcp_server.Github")
def test_repo_property_returns_none_when_nothing_configured(mock_github_cls, _isolated_chroma_path):
    server = MCPGithubServer(github_token="tok")

    assert server.repo is None


@pytest.mark.asyncio
@patch("app.services.mcp_server.Github")
async def test_tool_methods_return_graceful_error_when_no_repo_configured(
    mock_github_cls, _isolated_chroma_path
):
    server = MCPGithubServer(github_token="tok")

    issue_result = await server.get_issue(1)
    prs_result = await server.get_pull_requests()

    assert "error" in issue_result
    assert "error" in prs_result[0]


@patch("app.services.mcp_server.Github")
def test_repo_property_switches_after_new_ingest(mock_github_cls, _isolated_chroma_path):
    manifest = FileRepoManifest(_manifest_path(_isolated_chroma_path))
    manifest.add_files(["a.py"], "https://github.com/foo/repo-a")

    mock_client = mock_github_cls.return_value
    mock_client.get_repo.side_effect = lambda full_name: MagicMock(full_name=full_name)

    server = MCPGithubServer(github_token="tok")
    first = server.repo
    assert first.full_name == "foo/repo-a"

    # Simulate a fresh ingest happening via a different manifest instance
    # (mirrors ingest.py using its own FileRepoManifest instance).
    other_manifest = FileRepoManifest(_manifest_path(_isolated_chroma_path))
    other_manifest.add_files(["b.py"], "https://github.com/foo/repo-b")

    second = server.repo
    assert second.full_name == "foo/repo-b"
    assert mock_client.get_repo.call_count == 2


@patch("app.services.mcp_server.Github")
def test_repo_property_caches_when_unchanged(mock_github_cls, _isolated_chroma_path):
    manifest = FileRepoManifest(_manifest_path(_isolated_chroma_path))
    manifest.add_files(["a.py"], "https://github.com/foo/bar")

    mock_client = mock_github_cls.return_value
    mock_client.get_repo.return_value = MagicMock()

    server = MCPGithubServer(github_token="tok")
    server.repo
    server.repo

    mock_client.get_repo.assert_called_once_with("foo/bar")


def test_get_repo_for_file_uses_shared_helper(_isolated_chroma_path):
    with patch("app.services.mcp_server.Github"):
        manifest = FileRepoManifest(_manifest_path(_isolated_chroma_path))
        manifest.add_files(["shared/a.py"], "https://github.com/other/repo")
        manifest.add_files(["b.py"], "https://github.com/foo/bar")  # becomes last_repo_url

        server = MCPGithubServer(github_token="tok")

        owner, name = server._get_repo_for_file("shared/a.py")
        assert (owner, name) == ("other", "repo")
