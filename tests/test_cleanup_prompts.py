"""默认提示词的装配与工程契约回归；不把静态断言当作模型质量验收。"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from src.config_loader import load_settings
from src.refine_inputs import DualAsrInput
from src.refine_utils import (
    PreReplacementSegment,
    RefinementInputPaths,
    build_single_pass_refine_prompt,
    load_markdown_assemble_prompt,
    load_refinement_prompt,
    locked_quotes_preserved,
)
from tests.helpers import write_minimal_settings


PROMPT_ROOT = Path(__file__).resolve().parents[1] / "config/default_prompts"
JSON_FIELDS = (
    "final_markdown", "section_map", "refinement_notes",
    "needs_review_sections", "deletion_candidates",
)
POLICY_FRAGMENTS = (
    "Apply corrections and light cleanup only to unlocked input",
    "Do not change the words or order of `locked_quote`",
    "Never unlock a passage yourself",
    "Adopt a clearly better-supported reading",
    "without requiring a uniquely recoverable verbatim original",
    "Negation, conditions, and causality must follow speech evidence",
    "do not add or remove them to improve an argument",
    "Do not substitute a name merely because it is more famous",
    "Do not favor one model by default, use majority voting",
    "Remove meaningless fillers and pure stutters",
    "Remove adjacent mechanical repetition only when it adds no meaning",
    "Preserve meaningful emphasis, self-correction",
    "Preserve the original sequence and alternation",
    "Do not merge across an intervening question or speaker turn",
    "Preserve distinctive wording in jokes",
    "A better-supported candidate may be used in the manuscript",
    "When equally supported alternatives change meaning",
    "Do not replace recoverable speech with broad ellipses",
    "Do not invent timestamps",
)


@pytest.mark.parametrize("filename", ["classify_and_correct.md", "final_cleanup.md", "conversation_cleanup.md"])
def test_public_default_templates_are_english(filename: str) -> None:
    policy = (PROMPT_ROOT / filename).read_text(encoding="utf-8")
    assert policy.isascii()
    assert "Simplified Chinese" in policy


def test_repository_defaults_load_without_private_prompt_files() -> None:
    settings = load_settings(project_root=PROMPT_ROOT.parents[1])
    assert load_refinement_prompt(settings) == (PROMPT_ROOT / "classify_and_correct.md").read_text().strip()
    for mode, filename in [("reference", "final_cleanup.md"), ("conversation", "conversation_cleanup.md")]:
        assert load_markdown_assemble_prompt(settings, content_type=mode) == (PROMPT_ROOT / filename).read_text().strip()
    assert all("config/default_prompts/" in path for path in settings.settings.prompts.model_dump().values())


def segment(text: str, *, locked: bool = False, index: int = 0) -> PreReplacementSegment:
    return PreReplacementSegment(
        segment_type="locked_quote" if locked else "unlocked_text",
        text=text,
        source_text=text,
        reference_text=text if locked else "",
        start_sentence_index=index,
        end_sentence_index=index,
    )


@pytest.mark.parametrize("content_type", ["reference", "conversation"])
@pytest.mark.parametrize("mode", ["single_no_reference", "single_reference", "dual_reference"])
@pytest.mark.parametrize("backend", ["codex_api", "agy", "codex_cli"])
def test_default_editing_policy_reaches_each_prompt_without_conflicting_tail(
    tmp_path: Path, content_type: str, mode: str, backend: str,
) -> None:
    write_minimal_settings(tmp_path)
    filename = "conversation_cleanup.md" if content_type == "conversation" else "final_cleanup.md"
    policy = (PROMPT_ROOT / filename).read_text(encoding="utf-8").strip()
    (tmp_path / "config/prompts" / filename).write_text(policy, encoding="utf-8")
    settings = load_settings(project_root=tmp_path)
    assert load_markdown_assemble_prompt(settings, content_type=content_type) == policy

    asr_path = settings.path_for("asr_dir") / "demo.txt"
    reference_path = None if mode == "single_no_reference" else settings.path_for("extracted_text_dir") / "demo.txt"
    quote = "万物各有其理。"
    speech = "嗯，我，我不是说两个条件一样。"
    reference = "参考附件：万物各有其理。" if reference_path else ""
    parts = [segment(quote, locked=mode == "single_reference"), segment(speech, index=1)]
    dual = None
    if mode == "dual_reference":
        primary = {"model_size": "large-v3-turbo", "segments": [
            {"start": 0.0, "text": quote}, {"start": 61.0, "text": speech},
        ]}
        secondary = {"model_size": "Qwen/Qwen3-ASR-0.6B", "segments": [
            {"start": 0.5, "text": quote}, {"start": 62.0, "text": "我不是说两个条件一样。"},
        ]}
        dual = DualAsrInput(
            primary_path=asr_path.with_suffix(".json"),
            secondary_path=asr_path.parent / "secondary/qwen3-asr-0.6b/demo.json",
            primary_candidate="whisper-existing", secondary_candidate="qwen3-asr-0.6b",
            primary=primary, secondary=secondary, pair_run_id="prompt-fixture",
        )
        parts = []
    paths = RefinementInputPaths("demo", asr_path, reference_path, dual)
    prompt = build_single_pass_refine_prompt(
        policy, paths, backend=backend, pre_replaced_segments=parts, reference_full_text=reference,
    )

    assert prompt.startswith(policy) and prompt.count(policy) == 1
    for fragment in POLICY_FRAGMENTS:
        assert fragment in policy
    for field in JSON_FIELDS:
        assert policy.count(f"- `{field}`:") == 1
    assert prompt.count("字段必须包含") == 1
    for obsolete in ("只允许添加标点", "所有有效讲话、追问、回答、停顿后的补充", "结果会交给"):
        assert obsolete not in prompt
    # 装配不能代替模型做清理、改否定或重排证据。
    assert speech in prompt and prompt.index(quote) < prompt.index(speech)
    if mode == "dual_reference":
        assert dual.render() in prompt
        assert "[ASR A]" in prompt and "[ASR B]" in prompt
        assert "工程契约：不得改写 locked_quote" not in prompt
    elif mode == "single_reference":
        assert "[SEGMENT 01][locked_quote]" in prompt
        assert "[SEGMENT 02][unlocked_text]" in prompt
        assert "工程契约：不得改写 locked_quote 的实词内容" in prompt
    else:
        assert "[SEGMENT 01]" in prompt and "本任务没有参考附件" in prompt
    if reference_path:
        assert reference in prompt
    else:
        assert "参考附件：" not in prompt


@pytest.mark.parametrize("filename", ["final_cleanup.md", "conversation_cleanup.md"])
def test_policies_do_not_embed_job_ids_or_private_paths(filename: str) -> None:
    policy = (PROMPT_ROOT / filename).read_text(encoding="utf-8")
    assert not re.search(r"\b[0-9a-f]{12}\b", policy)
    assert not re.search(r"(?:data/jobs/|/home/|/Users/|[A-Z]:\\Users\\)", policy)


@pytest.mark.parametrize("content_type", ["reference", "conversation"])
def test_new_editorial_autonomy_still_respects_locked_quote_validation(
    tmp_path: Path, content_type: str,
) -> None:
    write_minimal_settings(tmp_path)
    filename = "conversation_cleanup.md" if content_type == "conversation" else "final_cleanup.md"
    policy = (PROMPT_ROOT / filename).read_text(encoding="utf-8").strip()
    parts = [segment("万物各有其理。", locked=True), segment("嗯，我，我不是说两个条件一样。", index=1)]
    paths = RefinementInputPaths("demo", tmp_path / "demo.txt", tmp_path / "reference.txt")
    prompt = build_single_pass_refine_prompt(
        policy, paths, backend="codex_api", pre_replaced_segments=parts, reference_full_text="万物各有其理。",
    )
    assert "Do not change the words or order of `locked_quote`" in prompt
    assert "Never unlock a passage yourself" in prompt
    assert "Reference/OCR corrections" in prompt
    assert locked_quotes_preserved(
        "> 万物各有其理。\n\n我不是说两个条件一样。", parts,
    )
    assert not locked_quotes_preserved(
        "> 万物没有规律。\n\n我不是说两个条件一样。", parts,
    )
