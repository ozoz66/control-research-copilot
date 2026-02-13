# -*- coding: utf-8 -*-
"""
Unit tests for local RAG engine.
"""

from dataclasses import dataclass
from pathlib import Path

from core.rag import (
    LocalRAGEngine,
    RAGSettings,
    build_rag_context,
    settings_from_api_config,
)


@dataclass
class DummyConfig:
    rag_enabled: bool = True
    rag_top_k: int = 3
    rag_min_score: float = 0.08
    rag_max_chunks_per_file: int = 2
    rag_chunk_size: int = 200
    rag_chunk_overlap: int = 20
    rag_max_context_chars: int = 1200
    rag_max_file_size_kb: int = 256
    rag_paths: list[str] = None
    rag_include_globs: list[str] = None


def test_settings_from_api_config_defaults():
    cfg = DummyConfig(rag_paths=["./docs"])
    settings = settings_from_api_config(cfg)
    assert settings.enabled is True
    assert settings.top_k == 3
    assert settings.min_score == 0.08
    assert settings.max_chunks_per_file == 2
    assert settings.chunk_size == 200
    assert settings.source_paths == ("./docs",)


def test_local_rag_retrieve(tmp_path: Path):
    kb = tmp_path / "kb"
    kb.mkdir()
    (kb / "a.md").write_text(
        "Sliding mode control can suppress disturbance and uncertainty in nonlinear systems.",
        encoding="utf-8",
    )
    (kb / "b.md").write_text(
        "Model predictive control is good for constrained optimization with receding horizon.",
        encoding="utf-8",
    )

    settings = RAGSettings(
        enabled=True,
        top_k=1,
        source_paths=(str(kb),),
        include_globs=("*.md",),
        chunk_size=500,
        chunk_overlap=0,
    )
    engine = LocalRAGEngine(settings)
    hits = engine.retrieve("disturbance rejection with sliding mode")
    assert len(hits) == 1
    assert "Sliding mode control" in hits[0].text


def test_build_rag_context(tmp_path: Path):
    kb = tmp_path / "kb"
    kb.mkdir()
    (kb / "notes.txt").write_text(
        "Extended state observer can estimate total disturbance in ADRC-style design.",
        encoding="utf-8",
    )

    cfg = DummyConfig(
        rag_enabled=True,
        rag_paths=[str(kb)],
        rag_include_globs=["*.txt"],
    )
    context = build_rag_context("how to estimate disturbance", cfg)
    assert "source:" in context
    assert "observer" in context.lower()


def test_local_rag_retrieve_diversifies_by_file(tmp_path: Path):
    kb = tmp_path / "kb"
    kb.mkdir()
    (kb / "a.md").write_text(
        ("disturbance observer robust control " * 80).strip(),
        encoding="utf-8",
    )
    (kb / "b.md").write_text(
        "Use observer design with anti-disturbance compensation.",
        encoding="utf-8",
    )

    settings = RAGSettings(
        enabled=True,
        top_k=2,
        max_chunks_per_file=1,
        source_paths=(str(kb),),
        include_globs=("*.md",),
        chunk_size=120,
        chunk_overlap=0,
    )
    engine = LocalRAGEngine(settings)
    hits = engine.retrieve("disturbance observer control")
    assert len(hits) == 2
    assert len({h.path for h in hits}) == 2
