from manovarta_core.config import RuntimeConfig
from manovarta_core.llm import HuggingFaceExtractor, HuggingFaceResponder


def _disabled_config():
    return RuntimeConfig(
        model_provider="huggingface",
        chat_model="Qwen/Qwen2.5-7B-Instruct",
        hf_token=None,
        hf_timeout=30.0,
        assistant_temperature=0.2,
        assistant_max_tokens=180,
    )


def test_huggingface_responder_stays_disabled_without_token():
    responder = HuggingFaceResponder(_disabled_config())
    assert responder.enabled is False


def test_huggingface_extractor_stays_disabled_without_token():
    extractor = HuggingFaceExtractor(_disabled_config())
    assert extractor.enabled is False
