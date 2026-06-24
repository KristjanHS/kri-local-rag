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

    with open(compose_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    services = data.get("services", {}) if isinstance(data, dict) else {}

    weaviate_ports = services.get("weaviate", {}).get("ports", [])
    ollama_ports = services.get("ollama", {}).get("ports", [])
    app_ports = services.get("app", {}).get("ports", [])

    # Host ports are parametrized (e.g. "127.0.0.1:${WEAVIATE_HTTP_HOST_PORT:-8080}:8080")
    # so the test profile can run on distinct host ports. The security property is the
    # loopback (127.0.0.1) binding prefix; the container-side port suffix stays fixed.
    def binds_loopback(ports: list[object], container_port: int) -> bool:
        return any(str(p).startswith("127.0.0.1:") and str(p).endswith(f":{container_port}") for p in ports)

    assert binds_loopback(weaviate_ports, 8080), "Weaviate must bind to loopback"
    assert binds_loopback(weaviate_ports, 50051), "Weaviate gRPC must bind to loopback"
    assert binds_loopback(ollama_ports, 11434), "Ollama must bind to loopback"

    # Streamlit app should be published (no strict binding required here)
    assert any(":8501" in str(p) for p in app_ports), "App should publish port 8501"
