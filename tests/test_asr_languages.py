from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from pydantic import ValidationError

from src.asr.qwen3_backend import QwenBackend, QwenGenerationLimitError
from src.asr.registry import candidate_options, get_candidate
from src.asr.segmentation import aligned_segments
from src.asr_utils import transcribe_audio_file
from src.config_loader import load_settings
from src.settings_overrides import ModelOverrides, SettingsOverrideError, apply_model_overrides, apply_model_overrides_to_raw_settings
from src.web.frontend_settings import FrontendSettingsUpdate, frontend_settings_response, save_frontend_settings
from src.web.models import AsrSelection
from tests.helpers import write_minimal_settings

ROOT = Path(__file__).resolve().parents[1]


def test_web_default_flows_into_job_snapshot_but_rerun_inherits_original(tmp_path, monkeypatch):
    from api_server import create_app
    from tests.test_api_server import request_json
    write_minimal_settings(tmp_path)
    video = tmp_path / 'sample.mp4'
    video.write_bytes(b'fixture')
    seen = []
    def stage(name, loaded, logger, **kwargs):
        seen.append(loaded.settings.asr.language)
        if name == 'export-markdown':
            directory = loaded.path_for('final_dir')
            directory.mkdir(parents=True, exist_ok=True)
            (directory / 'source.md').write_text('# Quiet morning\n')
        return 0
    monkeypatch.setattr('src.web.tasks.run_stage', stage)
    app = create_app(project_root=tmp_path, run_tasks_inline=True)
    assert request_json(app, 'PUT', '/api/frontend-settings', json_body={'asr_language': 'ja'}).status_code == 200
    response = request_json(app, 'POST', '/api/jobs', json_body={'video': str(video), 'output_dir': str(tmp_path / 'out'), 'content_type': 'conversation'})
    assert response.status_code == 202
    assert seen and set(seen) == {'ja'}
    job_id = response.json()['job_id']
    snapshot = load_settings(settings_path=tmp_path / 'data/jobs' / job_id / 'settings.generated.yaml', project_root=tmp_path)
    assert snapshot.settings.asr.language == 'ja'
    state = request_json(app, 'GET', f'/api/jobs/{job_id}').json()
    assert state['request_payload']['asr_language'] == 'ja'
    request_json(app, 'PUT', '/api/frontend-settings', json_body={'asr_language': 'en'})
    seen.clear()
    response = request_json(app, 'POST', f'/api/jobs/{job_id}/rerun', json_body={'start_stage': 'transcribe'})
    assert response.status_code == 202
    assert seen and set(seen) == {'ja'}


def test_manifest_item_languages_override_batch_default_and_are_snapshotted(tmp_path):
    from src.job_runner import validate_manifest_job_entry, prepare_batch_jobs
    write_minimal_settings(tmp_path)
    specs = []
    for index, language in enumerate(['en', 'ja', None]):
        video = tmp_path / f'sample-{index}.mp4'
        video.write_bytes(b'fixture')
        item = {'video': str(video), 'output_dir': str(tmp_path / 'out'), 'content_type': 'conversation'}
        if language:
            item['asr_language'] = language
        spec = validate_manifest_job_entry(item=item, default_content_type='conversation', default_book_name=None, default_chapter=None, default_glossary_file=None)
        assert spec.asr_language == language
        specs.append(spec)
    runtimes = prepare_batch_jobs(project_root=tmp_path, base_loaded_settings=load_settings(project_root=tmp_path), job_specs=specs, model_overrides=ModelOverrides(asr_language='auto'))
    assert len(runtimes) == 3 and all(runtime.status == 'pending' for runtime in runtimes)
    assert [load_settings(settings_path=runtime.job_root / 'settings.generated.yaml', project_root=tmp_path).settings.asr.language for runtime in runtimes] == ['en', 'ja', 'auto']


@pytest.mark.parametrize('language', ['', 'English', 12])
def test_manifest_rejects_invalid_language_codes(language):
    from src.job_runner import validate_manifest_job_entry, JobRunnerError
    with pytest.raises(JobRunnerError, match='语言|language'):
        validate_manifest_job_entry(item={'video': 'sample.mp4', 'output_dir': 'out', 'content_type': 'conversation', 'asr_language': language}, default_content_type='conversation', default_book_name=None, default_chapter=None, default_glossary_file=None)


@pytest.mark.parametrize('text', ['A quiet morning. The next step is ready.', 'しずかな朝です。次の準備をします。', 'おはよう。ありがとう。', 'I\nam ready.', 'Hello 世界。'])
def test_ocr_cleanup_preserves_english_japanese_and_mixed_source(text):
    from src.reference_utils import sanitize_gemini_ocr_text
    assert sanitize_gemini_ocr_text(text) == text


@pytest.mark.parametrize('file_mode', [False, True])
@pytest.mark.parametrize('language', ['auto', 'en', 'ja'])
def test_stage_requests_reach_execution_and_frozen_settings(tmp_path, monkeypatch, file_mode, language):
    from api_server import create_app
    from tests.test_api_server import request_json
    write_minimal_settings(tmp_path)
    seen = []
    def stage(name, loaded, logger, **kwargs):
        seen.append(loaded.settings.asr.language)
        directory = loaded.path_for('asr_dir')
        directory.mkdir(parents=True, exist_ok=True)
        (directory / 'sample.txt').write_text('おはよう。')
        return 0
    monkeypatch.setattr('src.web.tasks.run_stage', stage)
    app = create_app(project_root=tmp_path, run_tasks_inline=True)
    payload = {'asr_language': language}
    if file_mode:
        from tests.test_stage_file_runs import staged_file
        audio = staged_file(tmp_path, 'transcribe', 'audio', 'sample.wav', 'fixture')
        payload.update(input_files={'audio': str(audio)}, result_name='sample')
    suffix = '/file-run' if file_mode else ''
    response = request_json(app, 'POST', '/api/stages/transcribe' + suffix, json_body=payload)
    assert response.status_code == 202
    assert seen == [language]
    state = request_json(app, 'GET', '/api/stage-runs/' + response.json()['run_id']).json()
    assert state['status'] == 'success'
    assert state['request_payload']['asr_language'] == language
    snapshot = load_settings(settings_path=state['request_payload']['config'], project_root=tmp_path)
    assert snapshot.settings.asr.language == language


def test_ocr_language_configuration_is_independent_of_audio(tmp_path):
    from src.reference_utils import get_ocr_language_code
    write_minimal_settings(tmp_path, reference_overrides={'ocr_languages': ['jpn', 'eng']})
    loaded = load_settings(project_root=tmp_path)
    apply_model_overrides(loaded, ModelOverrides(asr_language='en'))
    assert get_ocr_language_code(loaded) == 'jpn+eng'


def test_dynamic_edit_prompts_do_not_force_chinese(tmp_path):
    from src.refine_utils import RefinementBlock, RefinementInputPaths, build_minimal_edit_prompt, build_markdown_assemble_prompt
    paths = RefinementInputPaths('sample', tmp_path / 'sample.txt', None)
    prompt = build_minimal_edit_prompt('', paths, RefinementBlock(1, 'A quiet morning.', '', ''), reference_full_text='')
    assert '英语、日语及混合语段不得翻译' in prompt
    prompt = build_markdown_assemble_prompt('', paths, edited_plain_text='おはよう。', reference_full_text='')
    assert '标题、段落和问答标签沿用正文语言' in prompt


def test_api_reports_audio_language_contract(tmp_path):
    from api_server import create_app
    from tests.test_api_server import request_json
    write_minimal_settings(tmp_path)
    response = request_json(create_app(project_root=tmp_path), 'GET', '/api/config')
    assert response.status_code == 200
    assert response.json()['asr_languages'] == ['auto', 'zh', 'en', 'ja']
    assert response.json()['default_asr_language'] == 'zh'


@pytest.mark.parametrize('language', ['auto', 'zh', 'en', 'ja'])
def test_request_and_settings_language_round_trip(tmp_path, language):
    write_minimal_settings(tmp_path)
    assert AsrSelection(asr_language=language).model_dump()['asr_language'] == language
    save_frontend_settings(tmp_path, FrontendSettingsUpdate(asr_language=language))
    assert frontend_settings_response(tmp_path)['asr_language'] == language
    loaded = load_settings(project_root=tmp_path)
    apply_model_overrides(loaded, ModelOverrides(asr_language=language))
    assert loaded.settings.asr.language == language
    raw = {'asr': {'language': 'zh'}}
    apply_model_overrides_to_raw_settings(raw, ModelOverrides(asr_language=language))
    assert raw['asr']['language'] == language


def test_omitted_language_inherits_config_and_never_resets_legacy_whisper_language(tmp_path):
    write_minimal_settings(tmp_path)
    loaded = load_settings(project_root=tmp_path)
    assert frontend_settings_response(tmp_path)['asr_language'] == 'zh'
    loaded.settings.asr.language = 'fr'
    apply_model_overrides(loaded, ModelOverrides())
    assert loaded.settings.asr.language == 'fr'
    raw = {'asr': {'language': 'fr'}}
    apply_model_overrides_to_raw_settings(raw, ModelOverrides())
    assert raw['asr']['language'] == 'fr'


@pytest.mark.parametrize('language', ['', 'Chinese', 'de'])
def test_web_language_rejects_unknown_codes(language):
    with pytest.raises(ValidationError):
        AsrSelection(asr_language=language)


@pytest.mark.parametrize('candidate,language', [('paraformer-zh', 'ja'), ('paraformer-zh', 'auto'), ('qwen3-asr-0.6b', 'fr')])
def test_unsupported_language_fails_before_mutating_settings(tmp_path, candidate, language):
    write_minimal_settings(tmp_path)
    loaded = load_settings(project_root=tmp_path)
    before = loaded.settings.asr.model_dump()
    with pytest.raises(SettingsOverrideError, match='language|语言'):
        apply_model_overrides(loaded, ModelOverrides(asr_candidate=candidate, asr_language=language))
    assert loaded.settings.asr.model_dump() == before


def test_secondary_candidate_language_is_validated(tmp_path):
    write_minimal_settings(tmp_path)
    loaded = load_settings(project_root=tmp_path)
    with pytest.raises(SettingsOverrideError, match='language|语言'):
        apply_model_overrides(loaded, ModelOverrides(asr_language='en', secondary_asr_candidate='paraformer-zh'))


@pytest.mark.parametrize('language,sdk_language', [('auto', None), ('en', 'en'), ('ja', 'ja'), ('zh', 'zh'), ('fr', 'fr')])
def test_whisper_language_parameters_and_metadata(tmp_path, language, sdk_language):
    write_minimal_settings(tmp_path)
    loaded = load_settings(project_root=tmp_path)
    loaded.settings.asr.language = language
    calls = []
    def recognize(*args, **kwargs):
        calls.append(kwargs)
        return iter([SimpleNamespace(id=1, start=0., end=1., text='A quiet morning.')]), SimpleNamespace(language='en')
    result = transcribe_audio_file(tmp_path / 'sample.wav', SimpleNamespace(transcribe=recognize), loaded)
    assert calls[0]['language'] == sdk_language
    assert result.language == 'en'
    assert result.metadata['requested_language'] == language
    assert result.metadata['reported_languages'] == ['en']
    assert result.metadata['detected_language'] == ('en' if language == 'auto' else None)


def qwen(language):
    backend = QwenBackend.__new__(QwenBackend)
    backend.candidate = get_candidate('qwen3-asr-0.6b')
    backend.language = language
    backend.chunk_seconds, backend.chunk_limit, backend.limit, backend.dtype = 2, 180, 2048, 'float16'
    backend.chunk_intervals = [[0, 2]]
    return backend


@pytest.mark.parametrize('language,sdk_language,reported', [('zh', 'Chinese', 'Chinese'), ('en', 'English', 'English'), ('ja', 'Japanese', 'Japanese'), ('auto', None, 'Japanese')])
def test_qwen_language_mapping_and_sdk_report(language, sdk_language, reported):
    backend = qwen(language)
    calls = []
    def recognize(**kwargs):
        calls.append(kwargs)
        return [SimpleNamespace(text='静かな朝です。', language=reported, time_stamps=None)]
    backend.model = SimpleNamespace(transcribe=recognize)
    segments, metadata = backend.transcribe(np.ones(20), 10, 2, [], [{'start': 0, 'end': 20}])
    assert segments[0]['text'] == '静かな朝です。'
    assert calls[0]['language'] == sdk_language
    assert metadata['requested_language'] == language
    assert metadata['reported_languages'] == [reported]
    assert metadata['detected_language'] == ('ja' if language == 'auto' else None)
    assert metadata['resolved_parameters']['language'] == sdk_language


@pytest.mark.parametrize('language', ['en', 'ja', 'auto'])
def test_non_chinese_qwen_does_not_use_chinese_generation_recovery(language):
    backend = qwen(language)
    calls = []
    def recognize(**kwargs):
        calls.append(kwargs)
        raise QwenGenerationLimitError('budget exhausted')
    backend.model = SimpleNamespace(transcribe=recognize)
    with pytest.raises(RuntimeError, match='budget exhausted'):
        backend.transcribe(np.ones(20), 10, 2, ['neutral'], [{'start': 0, 'end': 20}])
    assert len(calls) == 1


@pytest.mark.parametrize('language', ['auto', 'zh', 'en', 'ja'])
def test_pinned_nano_uses_language_codes_not_latest_sdk_names(monkeypatch, language):
    import sys
    from src.asr.funasr_backend import FunasrBackend
    monkeypatch.setitem(sys.modules, 'torch', SimpleNamespace(from_numpy=lambda a: a, any=np.any))
    backend = FunasrBackend.__new__(FunasrBackend)
    backend.candidate = get_candidate('fun-asr-nano')
    backend.language, backend.chunk_seconds, backend.limit = language, 2, 2048
    backend.decoder_dtype, backend.punc = 'fp32', None
    calls = []
    def generate(**kwargs):
        calls.append(kwargs)
        return [{'text': 'A quiet morning.'}]
    backend.model = SimpleNamespace(generate=generate)
    _, metadata = backend.transcribe(np.ones(20), 10, 2, [], [{'start': 0, 'end': 20}])
    assert calls[0]['language'] == language
    assert metadata['requested_language'] == language
    assert metadata['detected_language'] is None


@pytest.mark.parametrize('language,reported,expected', [('auto', 'Japanese', 'ja'), ('auto', '', 'auto'), ('en', 'English', 'en')])
def test_worker_preserves_requested_and_reported_language(monkeypatch, tmp_path, language, reported, expected):
    import sys
    from src.asr import worker
    seen = []
    class FakeBackend:
        def __init__(self, candidate, device, cache, parameters):
            seen.append(parameters['language'])
        def transcribe(self, *args):
            from src.asr.registry import language_metadata
            return [{'id': 1, 'start': 0., 'end': 1., 'text': 'A quiet morning.'}], language_metadata(language, [reported])
    monkeypatch.setitem(sys.modules, 'torch', SimpleNamespace(set_num_threads=lambda n: None, version=SimpleNamespace(cuda=None)))
    monkeypatch.setattr('src.asr.qwen3_backend.QwenBackend', FakeBackend)
    monkeypatch.setattr(worker.subprocess, 'run', lambda *a, **kw: SimpleNamespace(stdout=np.ones(16000, dtype='<f4').tobytes()))
    result, = worker.execute({'candidate': 'qwen3-asr-0.6b', 'device': 'cpu', 'cache': str(tmp_path), 'parameters': {'language': language}, 'language': language, 'terms': [], 'warnings': [], 'audio': [{'path': 'sample.wav', 'source_file': 'sample.wav', 'speech_detected': True, 'speech_regions_samples': [{'start': 0, 'end': 16000}]}]})
    assert seen == [language]
    assert result['language'] == expected
    assert result['metadata']['requested_language'] == language
    assert result['metadata']['reported_languages'] == ([reported] if reported else [])


def test_optional_request_carries_language_to_worker(tmp_path, monkeypatch):
    import src.asr_utils as asr
    from faster_whisper import audio, vad
    write_minimal_settings(tmp_path)
    loaded = load_settings(project_root=tmp_path)
    apply_model_overrides(loaded, ModelOverrides(asr_candidate='qwen3-asr-0.6b', asr_language='ja'))
    monkeypatch.setattr(audio, 'decode_audio', lambda *a, **k: np.ones(16000))
    monkeypatch.setattr(vad, 'get_speech_timestamps', lambda pcm: [{'start': 0, 'end': 16000}])
    seen = []
    def run(command, **kwargs):
        if '--request' not in command:
            return SimpleNamespace(returncode=0)
        request = json.loads(Path(command[command.index('--request')+1]).read_text())
        seen.append(request)
        response = [{'source_file': 'sample.wav', 'engine': 'qwen-asr', 'model_size': 'qwen', 'device': 'cpu', 'compute_type': 'float32', 'language': 'ja', 'segments': [{'id': 1, 'start': 0., 'end': 1., 'text': 'おはよう。'}], 'full_text': 'おはよう。', 'metadata': {'candidate': 'qwen3-asr-0.6b', 'duration_seconds': 1.}}]
        Path(command[command.index('--response')+1]).write_text(json.dumps(response))
        return SimpleNamespace(returncode=0, stderr='')
    monkeypatch.setattr(asr.subprocess, 'run', run)
    (tmp_path / 'sample.wav').write_bytes(b'fixture')
    output = tmp_path / 'result'
    output.mkdir()
    asr.transcribe_optional_backend([tmp_path / 'sample.wav'], output, loaded, None)
    assert seen[0]['language'] == seen[0]['parameters']['language'] == 'ja'


def test_legacy_whisper_language_survives_frozen_request_validation(tmp_path):
    from src.web.models import StageRunRequest
    from src.web.tasks import request_payload_with_effective_ocr_settings
    write_minimal_settings(tmp_path)
    loaded = load_settings(project_root=tmp_path)
    loaded.settings.asr.language = 'fr'
    payload = request_payload_with_effective_ocr_settings(StageRunRequest(), loaded, freeze_asr=True)
    assert StageRunRequest.model_validate(payload).asr_language is None
    assert payload['config'] == str(loaded.settings_path)


def test_invalid_secondary_language_is_rejected_before_any_primary_inference(tmp_path, monkeypatch):
    import src.asr_utils as asr
    write_minimal_settings(tmp_path)
    loaded = load_settings(project_root=tmp_path)
    loaded.settings.asr.language = 'en'
    loaded.settings.asr.secondary_candidate = 'paraformer-zh'
    loaded.path_for('audio_dir').mkdir(parents=True)
    (loaded.path_for('audio_dir') / 'sample.wav').write_bytes(b'fixture')
    calls = []
    monkeypatch.setattr(asr, 'transcribe_candidate_batch', lambda *a: calls.append('inference') or [])
    with pytest.raises(asr.AsrTranscriptionError, match='语言|language'):
        asr.transcribe_batch(loaded)
    assert calls == []


def test_reference_chunk_merge_keeps_english_spaces():
    from src.align_utils import split_text_by_punctuation
    assert split_text_by_punctuation('Is it ready? Yes! Next step.', 200) == ['Is it ready? Yes! Next step.']


@pytest.mark.parametrize('script', ['probe_asr_backends.py', 'check_docker_gpu.py'])
def test_diagnostic_scripts_expose_audio_language_without_model_calls(script):
    import subprocess
    import sys
    result = subprocess.run([sys.executable, str(ROOT / 'scripts' / script), '--help'], capture_output=True, text=True)
    assert result.returncode == 0
    assert '--asr-language' in result.stdout


def test_qwen_merged_language_report_is_not_misrepresented_as_one_detected_language():
    from src.asr.registry import language_metadata
    metadata = language_metadata('auto', ['Chinese,English', 'Japanese'])
    assert metadata['reported_languages'] == ['Chinese,English', 'Japanese']
    assert metadata['language'] == 'auto'
    assert metadata['detected_language'] is None
    assert metadata['detected_languages'] == ['zh', 'en', 'ja']


def test_language_capabilities_exposed_without_loading_models(tmp_path):
    write_minimal_settings(tmp_path)
    options = candidate_options(load_settings(project_root=tmp_path))
    assert all(option['supported_languages'] == ['auto', 'zh', 'en', 'ja'] for option in options)


@pytest.mark.parametrize('filename', ['00_run_main_pipeline.py', '02_transcribe.py', '06_refine.py', '08_run_job.py', '09_run_batch_jobs.py', 'run_pipeline.py'])
def test_cli_accepts_independent_audio_language(filename):
    spec = importlib.util.spec_from_file_location('language_cli', ROOT / 'scripts' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    parser = module.build_parser()
    # parse_known_args still enforces unrelated required arguments: inspect the actual action instead.
    action = next((a for a in parser._actions if '--asr-language' in a.option_strings), None)
    assert action is not None
    assert action.default is None


def test_zero_duration_merge_preserves_english_word_boundary():
    text = 'One! Two? Three.'
    segments = aligned_segments(text, [('One', 0., 1.), ('Two', 1., 1.), ('Three', 1., 2.)], 2.)
    assert segments[0]['text'] == 'One! Two?'


def test_english_sentence_split_keeps_words_and_decimal():
    from src.refine_utils import split_text_into_sentences
    assert split_text_into_sentences('Value is 3.5 units. Next step is ready.') == ['Value is 3.5 units.', 'Next step is ready.']


@pytest.mark.parametrize('directory', ['default_prompts'])
@pytest.mark.parametrize('filename', ['classify_and_correct.md', 'conversation_cleanup.md', 'final_cleanup.md'])
def test_public_prompts_preserve_source_language(directory, filename):
    text = (ROOT / 'config' / directory / filename).read_text()
    assert '统一输出为简体中文' not in text
    assert '使用简体中文；正文' not in text
    assert ('do not translate' in text.lower() or '不得翻译' in text)
    assert ('Japanese' in text or '日语' in text)
