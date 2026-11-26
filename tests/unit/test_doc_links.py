#!/usr/bin/env python3
"""Guard: every relative Markdown link in tracked ``README.md`` + ``docs/**/*.md`` resolves to a
tracked file or directory. Web, mailto and pure-anchor links are skipped; anchors are not checked."""

from __future__ import annotations

import posixpath
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import unquote

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
LINK_TARGET = re.compile(r"\]\(\s*<?([^)\s>]*)")
FENCED_BLOCK = re.compile(r"^(```|~~~).*?^\1", re.MULTILINE | re.DOTALL)
INLINE_CODE = re.compile(r"`[^`\n]*`")
SKIP_PREFIXES = ("http://", "https://", "mailto:", "#")


def _tracked_files() -> list[str]:
    if shutil.which("git") is None or not (REPO_ROOT / ".git").exists():
        pytest.skip("not a git checkout; doc link guard needs `git ls-files`")
    out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "-z"],
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8")
    return [f for f in out.split("\0") if f]


def _doc_pages(tracked: list[str]) -> list[str]:
    return [f for f in tracked if f == "README.md" or (f.startswith("docs/") and f.endswith(".md"))]


def _dead_links(root: Path, pages: list[str], tracked: set[str]) -> list[tuple[str, str]]:
    tracked_dirs = {d for f in tracked for d in _parents(f)}
    dead: list[tuple[str, str]] = []
    for rel in pages:
        text = (root / rel).read_text(encoding="utf-8")
        text = INLINE_CODE.sub("", FENCED_BLOCK.sub("", text))
        for target in LINK_TARGET.findall(text):
            if not target or target.startswith(SKIP_PREFIXES):
                continue
            path = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if path.startswith("/"):
                resolved = posixpath.normpath(path.lstrip("/"))
            else:
                resolved = posixpath.normpath(posixpath.join(posixpath.dirname(rel), path))
            if resolved not in tracked and resolved not in tracked_dirs:
                dead.append((rel, target))
    return dead


def _parents(rel: str) -> list[str]:
    parts = rel.split("/")[:-1]
    return ["/".join(parts[: i + 1]) for i in range(len(parts))]


def test_doc_links_resolve_to_tracked_files():
    tracked = _tracked_files()
    pages = _doc_pages(tracked)
    assert "README.md" in pages, f"page selector missed README.md; selected {len(pages)} pages"
    dead = _dead_links(REPO_ROOT, pages, set(tracked))
    assert not dead, "dead relative doc links: " + "; ".join(f"{page} -> {target}" for page, target in dead)


def test_checker_reports_planted_dead_link(tmp_path: Path):
    page = tmp_path / "docs" / "page.md"
    page.parent.mkdir()
    page.write_text(
        "[ok](other.md) [up](../README.md#top) [dead](missing.md)\n"
        "[web](https://example.com) [mail](mailto:a@b.c) [anchor](#here) `[code](nope.md)`\n"
        "```\n[fenced](also-nope.md)\n```\n",
        encoding="utf-8",
    )
    tracked = {"README.md", "docs/page.md", "docs/other.md"}
    assert _dead_links(tmp_path, ["docs/page.md"], tracked) == [("docs/page.md", "missing.md")]
