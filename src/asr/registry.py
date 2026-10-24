"""Static, project-owned ASR candidates. Importing this module loads no model."""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


@dataclass(frozen=True)
class Candidate:
    id: str
    label: str
    engine: str
    model: str
    revision: str
    package: str
    supported_devices: tuple[str, ...] = ("cpu", "cuda")
    supported_languages: tuple[str, ...] = ("auto", "zh", "en", "ja")


CANDIDATES = {
    c.id: c for c in (
        Candidate("whisper-existing", "Whisper（现有运行配置）", "faster-whisper", "profile", "", "faster_whisper"),
        Candidate("qwen3-asr-1.7b", "Qwen3-ASR 1.7B", "qwen-asr", "Qwen/Qwen3-ASR-1.7B",
                  "7278e1e70fe206f11671096ffdd38061171dd6e5", "qwen_asr"),
        Candidate("qwen3-asr-0.6b", "Qwen3-ASR 0.6B", "qwen-asr", "Qwen/Qwen3-ASR-0.6B",
                  "5eb144179a02acc5e5ba31e748d22b0cf3e303b0", "qwen_asr"),
        Candidate("paraformer-zh", "Paraformer 中文（SeACo）", "funasr",
                  "iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
                  "v2.0.4", "funasr", supported_languages=("zh",)),
        Candidate("fun-asr-nano", "Fun-ASR-Nano 2512", "funasr", "FunAudioLLM/Fun-ASR-Nano-2512",
                  "272c57b82523ada6fd87095e955f8e29100979ab", "funasr"),
    )
}
# Presentation only: keep all candidates valid for CLI and saved task snapshots.
WEB_CANDIDATE_IDS = ("whisper-existing", "qwen3-asr-1.7b", "qwen3-asr-0.6b")
ALIGNER_MODEL = "Qwen/Qwen3-ForcedAligner-0.6B"
ALIGNER_REVISION = "c7cbfc2048c462b0d63a45797104fc9db3ad62b7"


def worker_python(loaded: Any) -> str:
    raw = os.environ.get("TRANSCRIPT_ASR_PYTHON") or loaded.settings.asr.worker_python
    if not raw:
        return sys.executable
    path = Path(raw).expanduser()
    # Preserve the venv executable symlink, rather than executing system Python.
    return str(path if path.is_absolute() else loaded.project_root / path)


def required_modules(candidate: Candidate) -> tuple[str, ...]:
    if candidate.id == "whisper-existing":
        return ("faster_whisper", "ctranslate2")
    modules = (candidate.package, "torch", "torchaudio", "transformers", "huggingface_hub", "numpy")
    return modules + (("modelscope",) if candidate.id == "paraformer-zh" else ())


def candidate_options(loaded: Any) -> list[dict[str, Any]]:
    interpreters = {sys.executable, worker_python(loaded)}
    availability = {}
    for interpreter in interpreters:
        try:
            check = subprocess.run([interpreter, "-c", "import importlib.util,json; "
                "print(json.dumps({n:importlib.util.find_spec(n) is not None for n in "
                "['faster_whisper','ctranslate2','qwen_asr','funasr','torch','torchaudio','transformers','huggingface_hub','numpy','modelscope']}))"], capture_output=True, text=True, timeout=10)
            availability[interpreter] = json.loads(check.stdout) if check.returncode == 0 else {}
        except (OSError, ValueError, subprocess.TimeoutExpired):
            availability[interpreter] = {}
    result = []
    for candidate_id in WEB_CANDIDATE_IDS:
        candidate = CANDIDATES[candidate_id]
        interpreter = sys.executable if candidate.id == "whisper-existing" else worker_python(loaded)
        dependencies = availability[interpreter]
        missing = [module for module in required_modules(candidate) if not dependencies.get(module)]
        status = "unknown" if not dependencies else "missing" if missing else "installed"
        result.append({"id": candidate.id, "label": candidate.label, "engine": candidate.engine,
                       "model": loaded.active_profile.asr_model_size if candidate.model == "profile" else candidate.model,
                       "supported_devices": list(candidate.supported_devices),
                       "supported_languages": list(candidate.supported_languages), "dependency_status": status,
                       "unavailable_reason": "" if status == "installed" else f"ASR 依赖未安装或无法检查: {interpreter} ({', '.join(missing)})",
                       "cache_status": "not_checked", "runtime_validation": "not_checked"})
    return result


ASR_LANGUAGES = ("auto", "zh", "en", "ja")
QWEN_LANGUAGES = {"auto": None, "zh": "Chinese", "en": "English", "ja": "Japanese"}


def validate_candidate_language(candidate: Candidate, language: str) -> None:
    if not language or (candidate.id != "whisper-existing" and language not in candidate.supported_languages):
        raise ValueError(f"候选 {candidate.id} 不支持音频语言 language={language!r}；"
                         f"可选值: {', '.join(candidate.supported_languages)}")
    # Whisper's existing config contract permits all SDK language codes. The
    # loaded model validates them, including English-only checkpoints.


def language_metadata(requested: str, reported: list[str]) -> dict[str, Any]:
    reported = list(dict.fromkeys(value for value in reported if value))
    codes = {name: code for code, name in QWEN_LANGUAGES.items() if name}
    # The pinned Qwen SDK may report a comma-separated language set per chunk.
    normalized = list(dict.fromkeys(codes.get(name.strip(), name.strip())
                                    for value in reported for name in value.split(",") if name.strip()))
    actual = normalized[0] if len(normalized) == 1 else "auto"
    return {"requested_language": requested, "reported_languages": reported,
            "detected_language": actual if requested == "auto" and len(normalized) == 1 else None,
            "detected_languages": normalized if requested == "auto" else [],
            "language": actual if normalized else requested}


def get_candidate(value: str | None) -> Candidate:
    key = value if value is not None else "whisper-existing"
    try:
        return CANDIDATES[key]
    except KeyError:
        raise ValueError(f"无效 ASR 候选: {key}。可选值: {', '.join(CANDIDATES)}") from None
