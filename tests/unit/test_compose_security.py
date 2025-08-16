"""Validate docker-compose service exposure per security checklist.

Ensures Weaviate and Ollama are bound to loopback only, and Streamlit is exposed.
"""

from __future__ import annotations

from pathlib import Path

import yaml


def test_compose_service_ports_binding_security() -> None:
    project_root = Path(__file__).resolve().parents[2]
    compose_path = project_root / "docker" / "docker-compose.yml"
    assert compose_path.exists(), "docker/docker-compose.yml should exist"

    with open(compute_str(compose_path), "r", encoding="utf-8") as f:  # type: ignore[name-defined]
        data = yaml.safe_load(f)
    services = data.get("services", {}) if isinstance(data, dict) else {}

    weaviate_ports = services.get("weaviate", {}).get("ports", [])
    ollama_ports = services.get("ollama", {}).get("ports", [])
    app_ports = services.get("app", {}).get("ports", [])

    assert any(str(p).startswith("127.0.0.1:8080:") for p in weaviate_ports), "Weaviate must bind to loopback"
    assert any(str(p).startswith("127.0.0.1:50051:") for p in weaviate_ports), "Weaviate gRPC must bind to loopback"
    assert any(str(p).startswith("127.0.0.1:11434:") for p in ollama_ports), "Ollama must bind to loopback"

    # Streamlit app should be published (no strict binding required here)
    assert any(":8501" in str(p) for p in app_ports), "App should publish port 8501"


# Helper to avoid mypy/pyright complaining when Path-like passed to yaml in typed mode
def compute_str(p: Path) -> str:
    return str(p)
