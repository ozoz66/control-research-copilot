# -*- coding: utf-8 -*-

from dataclasses import dataclass, field

from core.skills import build_local_skill_context


@dataclass
class DummySkillConfig:
    skill_enabled: bool = True
    skill_max_context_chars: int = 2000
    skill_max_files: int = 8
    skill_max_file_size_kb: int = 256
    skill_paths: list[str] = field(default_factory=list)
    skill_include_globs: list[str] = field(default_factory=lambda: ["*.md"])


def test_build_local_skill_context_disabled(tmp_path):
    skill_file = tmp_path / "style.md"
    skill_file.write_text("Always provide concise answers.", encoding="utf-8")

    cfg = DummySkillConfig(skill_enabled=False, skill_paths=[str(tmp_path)])
    assert build_local_skill_context(cfg, "architect") == ""


def test_build_local_skill_context_reads_files(tmp_path):
    (tmp_path / "global.md").write_text("Use equations when necessary.", encoding="utf-8")
    (tmp_path / "coder.md").write_text("Prefer deterministic code blocks.", encoding="utf-8")

    cfg = DummySkillConfig(skill_enabled=True, skill_paths=[str(tmp_path)])
    context = build_local_skill_context(cfg, "engineer")

    assert "Applicable local skills for agent 'engineer'" in context
    assert "Use equations when necessary." in context
    assert "Prefer deterministic code blocks." in context
    assert "[skill:global.md]" in context


def test_build_local_skill_context_respects_agent_filters(tmp_path):
    (tmp_path / "global.md").write_text("Always define symbols first.", encoding="utf-8")
    (tmp_path / "for_architect.md").write_text(
        "---\napply_to: [architect]\n---\nArchitect-only guidance.",
        encoding="utf-8",
    )
    (tmp_path / "for_engineer.md").write_text(
        "---\napply_to: [engineer]\n---\nEngineer-only guidance.",
        encoding="utf-8",
    )

    cfg = DummySkillConfig(skill_enabled=True, skill_paths=[str(tmp_path)])
    context = build_local_skill_context(cfg, "engineer")

    assert "Always define symbols first." in context
    assert "Engineer-only guidance." in context
    assert "Architect-only guidance." not in context


def test_build_local_skill_context_respects_priority_and_max_files(tmp_path):
    (tmp_path / "low.md").write_text(
        "---\npriority: 1\n---\nLow priority.",
        encoding="utf-8",
    )
    (tmp_path / "high.md").write_text(
        "---\npriority: 5\ntitle: High Priority Skill\n---\nHigh priority.",
        encoding="utf-8",
    )
    (tmp_path / "mid.md").write_text(
        "---\npriority: 3\n---\nMid priority.",
        encoding="utf-8",
    )

    cfg = DummySkillConfig(
        skill_enabled=True,
        skill_paths=[str(tmp_path)],
        skill_max_files=2,
    )
    context = build_local_skill_context(cfg, "engineer")

    assert "High priority." in context
    assert "Mid priority." in context
    assert "Low priority." not in context
    assert "[skill:High Priority Skill]" in context
