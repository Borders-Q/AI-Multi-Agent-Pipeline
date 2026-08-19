from skyt_platform.model_router import ModelRouter


def test_model_profiles_are_ordered_and_exclusions_are_respected():
    router = ModelRouter({"ollama": object(), "openai": object(), "critic": object()})
    assert router.select("strong") == "openai"
    assert router.select("strong", exclude={"openai"}) == "ollama"
    assert router.candidates("fast", exclude={"ollama"}) == ["openai", "critic"]


def test_unknown_profile_falls_back_to_available_client():
    router = ModelRouter({"local": object()})
    assert router.select("unknown") == "local"
