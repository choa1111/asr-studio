from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.classify_utils import (
    ClassificationInputEmptyError,
    build_classification_output_path,
    classify_batch,
    classify_block,
)
from src.config_loader import load_settings
from tests.helpers import write_minimal_settings


def make_block(
    *,
    asr_text: str,
    matched_reference_text: str = "",
    match_score: float = 0.0,
    match_status: str = "no_match",
    top_matches: list[dict] | None = None,
) -> dict:
    return {
        "block_id": 1,
        "start": 0.0,
        "end": 1.0,
        "asr_text": asr_text,
        "matched_reference_text": matched_reference_text,
        "match_score": match_score,
        "match_status": match_status,
        "top_matches": top_matches or [],
    }


def test_classify_batch_raises_when_aligned_dir_empty(tmp_path: Path) -> None:
    write_minimal_settings(tmp_path)
    (tmp_path / "data/intermediate/aligned").mkdir(parents=True, exist_ok=True)

    loaded_settings = load_settings(project_root=tmp_path)

    with pytest.raises(ClassificationInputEmptyError):
        classify_batch(loaded_settings)


def test_high_score_block_becomes_quote_candidate(tmp_path: Path) -> None:
    write_minimal_settings(tmp_path)
    loaded_settings = load_settings(project_root=tmp_path)
    block = make_block(
        asr_text="清晨微风起沿路看新芽",
        matched_reference_text="清晨微风起，沿路看新芽。",
        match_score=92.0,
        match_status="matched",
        top_matches=[
            {"ref_block_id": 1, "reference_text": "清晨微风起，沿路看新芽。", "score": 92.0},
            {"ref_block_id": 2, "reference_text": "沿途记录变化，晨光映新叶。", "score": 70.0},
        ],
    )

    result = classify_block(block, loaded_settings)

    assert result.classification == "quote_candidate"


def test_overlap_block_becomes_mixed_candidate(tmp_path: Path) -> None:
    write_minimal_settings(tmp_path)
    loaded_settings = load_settings(project_root=tmp_path)
    block = make_block(
        asr_text="清晨微风起沿路看新芽这句我们后面再看",
        matched_reference_text="清晨微风起，沿路看新芽。",
        match_score=68.0,
        match_status="weak_match",
        top_matches=[
            {"ref_block_id": 1, "reference_text": "清晨微风起，沿路看新芽。", "score": 68.0},
            {"ref_block_id": 2, "reference_text": "沿途记录变化，晨光映新叶。", "score": 63.0},
        ],
    )

    result = classify_block(block, loaded_settings)

    assert result.classification == "mixed_candidate"


def test_low_score_quote_like_block_is_not_defaulted_to_lecture(tmp_path: Path) -> None:
    write_minimal_settings(tmp_path)
    loaded_settings = load_settings(project_root=tmp_path)
    block = make_block(
        asr_text="晨光应新叶小径炎伸向前流过石桥转脚看湖面",
        matched_reference_text="小径延伸向前，树下清泉流过，远处是花园。走过石桥后，转角看湖面。",
        match_score=48.0,
        match_status="weak_match",
        top_matches=[
            {
                "ref_block_id": 4,
                "reference_text": "小径延伸向前，树下清泉流过，远处是花园。走过石桥后，转角看湖面。",
                "score": 48.0,
            },
            {"ref_block_id": 3, "reference_text": "沿途记录变化，晨光映新叶。", "score": 37.0},
            {"ref_block_id": 5, "reference_text": "看窗外，树影摇，鸟轻鸣。", "score": 29.0},
        ],
    )

    result = classify_block(block, loaded_settings)

    assert result.classification == "quote_candidate"


def test_continuous_quote_like_block_prefers_quote_candidate(tmp_path: Path) -> None:
    write_minimal_settings(tmp_path)
    loaded_settings = load_settings(project_root=tmp_path)
    block = make_block(
        asr_text="树影遥鸟清明过了几个路口回头是林间还可言湖慢步",
        matched_reference_text="看窗外，树影摇，鸟轻鸣。过了几个路口，回头是林间。还可沿湖漫步。",
        match_score=52.0,
        match_status="weak_match",
        top_matches=[
            {
                "ref_block_id": 6,
                "reference_text": "看窗外，树影摇，鸟轻鸣。过了几个路口，回头是林间。还可沿湖漫步。",
                "score": 52.0,
            },
            {"ref_block_id": 7, "reference_text": "也可停步观察，记录每一天。", "score": 41.0},
            {"ref_block_id": 8, "reference_text": "细节慢慢记，收获在眼前。", "score": 32.0},
        ],
    )

    result = classify_block(block, loaded_settings)

    assert result.classification == "quote_candidate"


def test_low_score_explanatory_block_becomes_lecture_candidate(tmp_path: Path) -> None:
    write_minimal_settings(tmp_path)
    loaded_settings = load_settings(project_root=tmp_path)
    block = make_block(asr_text="这里的意思是作者在说明情绪变化", match_score=22.0, match_status="no_match")

    result = classify_block(block, loaded_settings)

    assert result.classification == "lecture_candidate"


def test_question_like_block_becomes_qa_candidate(tmp_path: Path) -> None:
    write_minimal_settings(tmp_path)
    loaded_settings = load_settings(project_root=tmp_path)
    block = make_block(asr_text="为什么这里要说沿路看新芽呢？", match_score=18.0, match_status="no_match")

    result = classify_block(block, loaded_settings)

    assert result.classification == "qa_candidate"


def test_intro_like_block_becomes_intro_candidate(tmp_path: Path) -> None:
    write_minimal_settings(tmp_path)
    loaded_settings = load_settings(project_root=tmp_path)
    block = make_block(asr_text="示例音频现在播送清晨观察短文", match_score=10.0, match_status="no_match")

    result = classify_block(block, loaded_settings)

    assert result.classification == "intro_candidate"


def test_intro_prefix_with_reference_overlap_stays_intro_or_mixed(tmp_path: Path) -> None:
    write_minimal_settings(tmp_path)
    loaded_settings = load_settings(project_root=tmp_path)
    block = make_block(
        asr_text="示例音频现在播送观察记录沿路看新芽清晨微风起沿路看新芽",
        matched_reference_text="清晨微风起，沿路看新芽。",
        match_score=63.0,
        match_status="weak_match",
        top_matches=[
            {"ref_block_id": 1, "reference_text": "清晨微风起，沿路看新芽。", "score": 63.0},
            {"ref_block_id": 2, "reference_text": "沿途记录变化，晨光映新叶。", "score": 46.0},
        ],
    )

    result = classify_block(block, loaded_settings)

    assert result.classification in {"intro_candidate", "mixed_candidate"}


def test_classify_batch_writes_expected_output_structure(tmp_path: Path) -> None:
    write_minimal_settings(tmp_path)
    aligned_dir = tmp_path / "data/intermediate/aligned"
    aligned_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "blocks": [
            make_block(
                asr_text="清晨微风起沿路看新芽",
                matched_reference_text="清晨微风起，沿路看新芽。",
                match_score=92.0,
                match_status="matched",
                top_matches=[{"ref_block_id": 1, "reference_text": "清晨微风起，沿路看新芽。", "score": 92.0}],
            )
        ]
    }
    (aligned_dir / "demo.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    loaded_settings = load_settings(project_root=tmp_path)

    summary = classify_batch(loaded_settings)
    output_path = build_classification_output_path(aligned_dir / "demo.json", tmp_path / "data/intermediate/classified")
    result = json.loads(output_path.json_path.read_text(encoding="utf-8"))

    assert summary.success == 1
    assert result["total_blocks"] == 1
    assert "source_aligned_file" in result
    assert "classified_blocks" in result
    assert "classification" in result["classified_blocks"][0]
    assert "classification_reason" in result["classified_blocks"][0]
    assert "confidence" in result["classified_blocks"][0]
