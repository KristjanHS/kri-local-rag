#!/usr/bin/env python3
from typing import Any, Dict

from backend import ingest as ing


def test_safe_created_at_handles_missing(tmp_path):
    # None or missing path should not raise and should return ISO string
    ts1 = ing._safe_created_at(None)
    assert isinstance(ts1, str) and "T" in ts1

    # Non-existent file
    missing = tmp_path / "nope.txt"
    ts2 = ing._safe_created_at(str(missing))
    assert isinstance(ts2, str) and "T" in ts2


def test_deterministic_uuid_stable():
    class Doc:
        page_content: str
        metadata: Dict[str, Any]

        def __init__(self, content: str, source: str) -> None:
            self.page_content = content
            self.metadata = {"source": source}

    d1 = Doc("hello", "/x/a.pdf")
    d2 = Doc("hello", "/x/a.pdf")
    d3 = Doc("hello", "/x/b.pdf")

    u1 = ing.deterministic_uuid(d1)  # type: ignore[arg-type]
    u2 = ing.deterministic_uuid(d2)  # type: ignore[arg-type]
    u3 = ing.deterministic_uuid(d3)  # type: ignore[arg-type]
    assert u1 == u2
    assert u1 != u3
