"""Unit tests for GitHub URL parsing helper."""

from app.services.github_url import parse_owner_repo


def test_parse_owner_repo_plain_url():
    assert parse_owner_repo("https://github.com/AnnaKitou/EShopMicrosrvices") == (
        "AnnaKitou",
        "EShopMicrosrvices",
    )


def test_parse_owner_repo_with_git_suffix():
    assert parse_owner_repo("https://github.com/owner/repo.git") == ("owner", "repo")


def test_parse_owner_repo_with_trailing_slash():
    assert parse_owner_repo("https://github.com/owner/repo/") == ("owner", "repo")


def test_parse_owner_repo_malformed_url_returns_none():
    assert parse_owner_repo("not-a-url") == (None, None)


def test_parse_owner_repo_empty_or_none_returns_none():
    assert parse_owner_repo("") == (None, None)
    assert parse_owner_repo(None) == (None, None)
