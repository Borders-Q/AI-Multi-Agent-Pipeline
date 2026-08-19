from agent.llm_client import identify_api_key, llm


def test_provider_detection_remains_stable():
    assert identify_api_key("sk-ant-example")[0] == "anthropic"
    assert identify_api_key("AIza-example")[0] == "gemini"


def test_ollama_client_bypasses_environment_proxy():
    ollama = llm.clients.get("ollama")
    assert ollama is not None
    http_client = getattr(ollama["client"], "_client", None)
    assert http_client is not None
    assert http_client._trust_env is False
