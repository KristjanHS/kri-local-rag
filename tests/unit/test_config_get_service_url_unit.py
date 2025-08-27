from __future__ import annotations

import importlib


def test_get_service_url_weaviate_default(monkeypatch):
    monkeypatch.delenv("WEAVIATE_URL", raising=False)
    from backend import config as cfg

    importlib.reload(cfg)
    assert cfg.get_service_url("weaviate") == "http://localhost:8080"


def test_get_service_url_weaviate_env_override(monkeypatch):
    monkeypatch.setenv("WEAVIATE_URL", "http://weaviate:8080")
    from backend import config as cfg

    importlib.reload(cfg)
    assert cfg.get_service_url("weaviate") == "http://weaviate:8080"
