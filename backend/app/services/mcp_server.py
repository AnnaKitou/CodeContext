"""
MCP (Model Context Protocol) Server: Integrates with GitHub API.

Provides tools for the LLM agent to access live repository data
(issues, PRs, git blame, commit history).
"""

import logging
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

from github import Github, GithubException

from app.core.config import settings
from app.services.manifest import FileRepoManifest

logger = logging.getLogger(__name__)


class MCPGithubServer:
    """
    MCP server that integrates GitHub API.

    Provides tools for accessing live repository information:
    - git blame (who last modified each line)
    - issues (search, fetch details)
    - pull requests (list, search)
    - commit history (for a file or globally)
    """

    def __init__(self, github_token: str, repo_owner: str, repo_name: str):
        """
        Initialize the MCP GitHub server.

        Args:
            github_token: GitHub personal access token
            repo_owner: Repository owner (user or org)
            repo_name: Repository name
        """
        self.github_token = github_token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.manifest = FileRepoManifest(
            f"{settings.CHROMA_DB_PATH}/file_repo_manifest.json"
        )

        try:
            # Initialize PyGithub client
            self.client = Github(github_token)
            self.repo = self.client.get_repo(f"{repo_owner}/{repo_name}")
            logger.info(f"Initialized GitHub client for {repo_owner}/{repo_name}")
        except GithubException as e:
            logger.error(f"Failed to initialize GitHub client: {str(e)}")
            self.client = None
            self.repo = None

    def _get_repo_for_file(self, file_path: str) -> tuple[Optional[str], Optional[str]]:
        """
        Get repo owner and name for a file by looking up its source repository.

        Args:
            file_path: Path to the file

        Returns:
            Tuple of (repo_owner, repo_name) or (None, None) if not found
        """
        repo_url = self.manifest.get_repo_url(file_path)
        if not repo_url:
            return None, None

        try:
            parsed = urlparse(repo_url)
            path_parts = parsed.path.strip("/").split("/")
            if len(path_parts) >= 2:
                owner = path_parts[-2]
                name = path_parts[-1].replace(".git", "")
                return owner, name
        except Exception as e:
            logger.warning(f"Failed to parse repo URL {repo_url}: {e}")

        return None, None

    async def get_file_blame(
        self, file_path: str, line_number: Optional[int] = None
    ) -> dict[str, Any]:
        """Get git blame information for a file."""
        logger.info(f"Getting blame for {file_path}")

        owner, name = self._get_repo_for_file(file_path)
        if not owner or not name:
            logger.warning(f"No repository found in manifest for {file_path}, using default")
            if not self.repo:
                return {"error": "GitHub client not initialized"}
            repo = self.repo
        else:
            try:
                repo = self.client.get_repo(f"{owner}/{name}")
            except GithubException as e:
                logger.warning(f"Failed to get repo {owner}/{name}: {e}, using default")
                if not self.repo:
                    return {"error": "GitHub client not initialized"}
                repo = self.repo

        try:
            commits = repo.get_commits(path=file_path)
            commit = commits[0]
            blame_info = {
                "file": file_path,
                "last_author": commit.commit.author.name if commit.commit.author else "Unknown",
                "last_email": commit.commit.author.email if commit.commit.author else "unknown@example.com",
                "last_commit": commit.sha[:7],
                "last_message": commit.commit.message.split("\n")[0],
                "last_date": commit.commit.author.date.isoformat() if commit.commit.author else None,
            }
            if line_number:
                blame_info["line_number"] = line_number
            return blame_info

        except GithubException as e:
            logger.error(f"Blame lookup failed: {str(e)}")
            return {"error": f"Failed to get blame: {str(e)}"}

    async def get_issue(self, issue_number: int) -> dict[str, Any]:
        """Fetch GitHub issue details."""
        logger.info(f"Getting issue #{issue_number}")

        if not self.repo:
            return {"error": "GitHub client not initialized"}

        try:
            issue = self.repo.get_issue(issue_number)
            return {
                "number": issue.number,
                "title": issue.title,
                "body": issue.body[:500] if issue.body else None,
                "state": issue.state,
                "author": issue.user.login,
                "created_at": issue.created_at.isoformat(),
                "updated_at": issue.updated_at.isoformat(),
                "labels": [label.name for label in issue.labels],
                "comments": issue.comments,
                "url": issue.html_url,
            }

        except GithubException as e:
            logger.error(f"Issue lookup failed: {str(e)}")
            return {"error": f"Failed to get issue: {str(e)}"}

    async def get_pull_requests(
        self,
        state: str = "open",
        keyword: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search for pull requests."""
        logger.info(f"Getting pull requests (state={state}, keyword={keyword})")

        if not self.repo:
            return [{"error": "GitHub client not initialized"}]

        try:
            github_state = "all" if state == "all" else state
            prs = self.repo.get_pulls(state=github_state, sort="updated", direction="desc")

            results = []
            count = 0

            for pr in prs:
                if keyword:
                    if keyword.lower() not in pr.title.lower() and keyword.lower() not in (pr.body or "").lower():
                        continue

                results.append({
                    "number": pr.number,
                    "title": pr.title,
                    "state": pr.state,
                    "author": pr.user.login,
                    "created_at": pr.created_at.isoformat(),
                    "updated_at": pr.updated_at.isoformat(),
                    "merged": pr.merged,
                    "url": pr.html_url,
                })

                count += 1
                if count >= limit:
                    break

            return results

        except GithubException as e:
            logger.error(f"PR search failed: {str(e)}")
            return [{"error": f"Failed to get PRs: {str(e)}"}]

    async def get_commit_history(
        self,
        file_path: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get commit history for a file."""
        logger.info(f"Getting commit history for {file_path}")

        owner, name = self._get_repo_for_file(file_path)
        if not owner or not name:
            logger.warning(f"No repository found in manifest for {file_path}")
            return [{"error": f"Repository not found for {file_path}"}]

        try:
            repo = self.client.get_repo(f"{owner}/{name}")
            commits = repo.get_commits(path=file_path)

            results = []
            for i, commit in enumerate(commits):
                if i >= limit:
                    break
                results.append({
                    "sha": commit.sha[:7],
                    "author": commit.commit.author.name if commit.commit.author else "Unknown",
                    "email": commit.commit.author.email if commit.commit.author else None,
                    "message": commit.commit.message.split("\n")[0],
                    "date": commit.commit.author.date.isoformat() if commit.commit.author else None,
                    "url": commit.html_url,
                })

            return results

        except GithubException as e:
            logger.error(f"Commit history failed: {str(e)}")
            return [{"error": f"Failed to get commit history: {str(e)}"}]

    async def execute_tool(self, tool_name: str, **kwargs) -> dict[str, Any]:
        """Execute a tool by name with given arguments."""
        if tool_name == "get_file_blame":
            return await self.get_file_blame(
                file_path=kwargs.get("file_path"),
                line_number=kwargs.get("line_number"),
            )
        elif tool_name == "get_issue":
            return await self.get_issue(issue_number=kwargs.get("issue_number"))
        elif tool_name == "get_pull_requests":
            return await self.get_pull_requests(
                state=kwargs.get("state", "open"),
                keyword=kwargs.get("keyword"),
                limit=kwargs.get("limit", 10),
            )
        elif tool_name == "get_commit_history":
            return await self.get_commit_history(
                file_path=kwargs.get("file_path"),
                limit=kwargs.get("limit", 10),
            )
        else:
            return {"error": f"Unknown tool: {tool_name}"}
