from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.config_loader import load_settings
from src.job_runner import (
    JobRunnerError,
    SUPPORTED_CONTENT_TYPES,
    normalize_content_type,
    validate_reference_contract,
)
from src.schemas import ClassificationSettings
from src.web.models import BatchJobRequest, SingleJobRequest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INTRO_KEYWORDS = ["现在播送", "下面播送", "标题", "作者", "今天我们", "今天继续"]


def test_reference_mode_is_the_default_across_job_contracts() -> None:
    assert SUPPORTED_CONTENT_TYPES == {"reference", "conversation"}
    assert normalize_content_type(None) == "reference"
    assert normalize_content_type(" REFERENCE ") == "reference"
    assert SingleJobRequest(video="sample.mp4", output_dir="output").content_type == "reference"
    assert BatchJobRequest().content_type == "reference"


def test_reference_mode_still_requires_reference_material() -> None:
    with pytest.raises(JobRunnerError, match="参考材料校对模式缺少必填字段: reference"):
        validate_reference_contract(content_type="reference", reference=None)
    validate_reference_contract(content_type="reference", reference="sample.txt")
    validate_reference_contract(content_type="conversation", reference=None)
    with pytest.raises(JobRunnerError, match="对谈模式不使用 reference"):
        validate_reference_contract(content_type="conversation", reference="sample.txt")


def test_default_intro_keywords_are_generic() -> None:
    settings = load_settings(project_root=PROJECT_ROOT)
    assert settings.settings.classification.intro_keywords == INTRO_KEYWORDS
    assert ClassificationSettings().intro_keywords == INTRO_KEYWORDS


@pytest.mark.parametrize("filename", ["settings.yaml", "setting.yaml"])
def test_default_export_title_is_generic(filename: str) -> None:
    config = yaml.safe_load((PROJECT_ROOT / "config" / filename).read_text(encoding="utf-8"))
    assert config["export"]["markdown_title_template"] == "# {book_name} {chapter} 整理稿"


def test_default_reference_prompt_has_a_generic_heading() -> None:
    policy = (PROJECT_ROOT / "config/default_prompts/final_cleanup.md").read_text(encoding="utf-8")
    assert policy.splitlines()[0] == "# Faithful reference-assisted transcript editing"
