#!/usr/bin/env python3
"""Guard: every cited dated doc (``YYYY-MM-DD-<slug>.md``) resolves to a tracked file.

Plans and design docs are cited by their dated filename from code comments, config
and other docs. When a doc is renamed, archived out of the tree or deleted, those
cites silently dangle. This test scans every git-tracked text file for dated-doc
cites and fails on any cite whose basename is not a tracked file.

``KNOWN_DANGLING`` pins dangles that existed when the guard was added, so the test
only fails on NEW ones. Shrink it when you fix a cite; never grow it to silence a
failure — fix the cite instead.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DATED_DOC_CITE = re.compile(r"\d{4}-\d{2}-\d{2}-[\w.-]+\.md")

# Dangling cites present when this guard was introduced (none at the time).
KNOWN_DANGLING: frozenset[str] = frozenset()


def _tracked_files() -> list[str]:
    if shutil.which("git") is None or not (REPO_ROOT / ".git").exists():
        pytest.skip("not a git checkout; dated-doc cite guard needs `git ls-files`")
    out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "-z"],
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8")
    return [f for f in out.split("\0") if f]


def _dangling_cites(tracked: list[str]) -> dict[str, list[str]]:
    tracked_basenames = {Path(f).name for f in tracked}
    dangling: dict[str, list[str]] = {}
    for rel in tracked:
        path = REPO_ROOT / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binary or unreadable: not a text cite source
        for cite in DATED_DOC_CITE.findall(text):
            if cite not in tracked_basenames:
                dangling.setdefault(cite, []).append(rel)
    return dangling


def test_dated_doc_cites_resolve_to_tracked_files():
    tracked = _tracked_files()
    dangling = _dangling_cites(tracked)
    new = {cite: files for cite, files in dangling.items() if cite not in KNOWN_DANGLING}
    assert not new, "dated-doc cites with no tracked file: " + "; ".join(
        f"{cite} (cited in {', '.join(sorted(set(files)))})" for cite, files in sorted(new.items())
    )


def test_known_dangling_baseline_is_still_dangling():
    """A baseline entry that now resolves (or is no longer cited) must be removed."""
    dangling = _dangling_cites(_tracked_files())
    stale = sorted(KNOWN_DANGLING - dangling.keys())
    assert not stale, f"KNOWN_DANGLING entries no longer dangle; drop them: {stale}"
