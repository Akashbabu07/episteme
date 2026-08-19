from app.config.settings import get_settings

def test_settings_load():
    settings = get_settings()
    assert settings.database_url.startswith("postgresql")
    assert settings.model_provider in ("ollama", "groq", "anthropic")
    assert settings.max_steps > 0


def test_ollama_defaults():
    settings = get_settings()
    assert settings.ollama_model