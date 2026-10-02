from types import SimpleNamespace

from app.config import Settings
from app import gemini


def test_output_cap_usage_and_old_call_compatibility(monkeypatch):
    configs = []
    def generate_content(**kwargs):
        configs.append(kwargs['config'])
        return SimpleNamespace(text='{"ok":true}', usage_metadata=SimpleNamespace(prompt_token_count=11, candidates_token_count=7, thoughts_token_count=3))
    monkeypatch.setattr(gemini, '_get_client', lambda settings: SimpleNamespace(models=SimpleNamespace(generate_content=generate_content)))
    usage = []
    settings = Settings.from_env()
    assert gemini.generate_json(settings, 'data', 'system', {}, 'test', max_output_tokens=2048, usage_sink=usage.append) == {'ok': True}
    assert configs[0].max_output_tokens == 2048
    assert usage == [{'input_tokens':11, 'output_tokens':7, 'thinking_tokens':3}]
    assert gemini.generate_json(settings, 'data', 'system', {}, 'legacy') == {'ok': True}
    assert configs[1].max_output_tokens is None


def test_gemini_client_receives_cloud_identity_credentials(monkeypatch):
    from dataclasses import replace
    from google import genai
    from app import cloud_identity
    credentials = object()
    monkeypatch.setattr(gemini, '_client', None)
    monkeypatch.setattr(cloud_identity, 'cloud_credentials', lambda: credentials)
    def client(**kwargs):
        assert kwargs['credentials'] is credentials
        return SimpleNamespace(project=kwargs['project'])
    monkeypatch.setattr(genai, 'Client', client)
    actual = gemini._get_client(replace(Settings.from_env(), gcp_project='repsafe-finshield-test'))
    assert actual.project == 'repsafe-finshield-test'
