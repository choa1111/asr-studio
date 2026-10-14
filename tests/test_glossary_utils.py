from __future__ import annotations

from pathlib import Path

from src.glossary_utils import build_initial_prompt, load_glossary_terms, merge_glossary_terms


def test_load_glossary_terms_ignores_blank_lines(tmp_path: Path) -> None:
    glossary = tmp_path / "terms.txt"
    glossary.write_text("示例甲\n\n示例乙\n  \n示例丙\n", encoding="utf-8")

    assert load_glossary_terms(glossary) == ["示例甲", "示例乙", "示例丙"]


def test_merge_glossary_terms_deduplicates_while_preserving_order() -> None:
    merged = merge_glossary_terms(
        ["示例甲", "示例乙"],
        ["示例乙", "示例丙"],
        ["示例丁"],
    )

    assert merged == ["示例甲", "示例乙", "示例丙", "示例丁"]


def test_build_initial_prompt_truncates_at_max_chars() -> None:
    prompt = build_initial_prompt(["示例甲", "示例乙", "术语", "较长示例术语"], max_chars=10)

    assert prompt == "示例甲，示例乙，术语"
