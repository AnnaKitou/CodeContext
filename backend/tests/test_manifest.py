"""Tests for FileRepoManifest: per-file repo lookup and last-ingested-repo tracking."""

import json

from app.services.manifest import FileRepoManifest


def test_add_files_sets_last_repo_url(tmp_path):
    manifest = FileRepoManifest(tmp_path / "manifest.json")
    manifest.add_files(["a.py"], "https://github.com/o/r")

    assert manifest.get_last_repo_url() == "https://github.com/o/r"
    assert manifest.get_repo_url("a.py") == "https://github.com/o/r"


def test_last_repo_url_updates_on_second_ingest(tmp_path):
    manifest = FileRepoManifest(tmp_path / "manifest.json")
    manifest.add_files(["a.py"], "https://github.com/o/repo-a")
    manifest.add_files(["b.py"], "https://github.com/o/repo-b")

    assert manifest.get_last_repo_url() == "https://github.com/o/repo-b"
    # Earlier files keep their original repo association.
    assert manifest.get_repo_url("a.py") == "https://github.com/o/repo-a"
    assert manifest.get_repo_url("b.py") == "https://github.com/o/repo-b"


def test_clear_resets_last_repo_url(tmp_path):
    manifest = FileRepoManifest(tmp_path / "manifest.json")
    manifest.add_files(["a.py"], "https://github.com/o/r")
    manifest.clear()

    assert manifest.get_last_repo_url() is None
    assert manifest.get_repo_url("a.py") is None


def test_legacy_flat_format_migrates_on_load(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({"a.py": "https://github.com/o/r"}))

    manifest = FileRepoManifest(manifest_path)

    assert manifest.get_repo_url("a.py") == "https://github.com/o/r"
    assert manifest.get_last_repo_url() is None


def test_cross_instance_freshness(tmp_path):
    """A long-lived instance must see writes made by a separate instance on the same file."""
    manifest_path = tmp_path / "manifest.json"
    writer = FileRepoManifest(manifest_path)
    reader = FileRepoManifest(manifest_path)

    writer.add_files(["a.py"], "https://github.com/o/repo-a")
    assert reader.get_last_repo_url() == "https://github.com/o/repo-a"
    assert reader.get_repo_url("a.py") == "https://github.com/o/repo-a"

    writer.add_files(["b.py"], "https://github.com/o/repo-b")
    assert reader.get_last_repo_url() == "https://github.com/o/repo-b"


def test_normalize_path_does_not_mangle_real_prefix_chars(tmp_path):
    manifest = FileRepoManifest(tmp_path / "manifest.json")
    manifest.add_files(["report.py", "temp.py"], "https://github.com/o/r")

    assert manifest.get_repo_url("report.py") == "https://github.com/o/r"
    assert manifest.get_repo_url("temp.py") == "https://github.com/o/r"


def test_normalize_path_still_strips_known_prefixes(tmp_path):
    manifest = FileRepoManifest(tmp_path / "manifest.json")
    manifest.add_files(["temp_repos/foo/bar.py", "./baz.py"], "https://github.com/o/r")

    assert manifest.get_repo_url("foo/bar.py") == "https://github.com/o/r"
    assert manifest.get_repo_url("baz.py") == "https://github.com/o/r"
