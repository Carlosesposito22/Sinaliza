import time

from app.model_provider import ModelProvider, create_provider


def wait_for(condition, seconds=3.0):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.01)
    return False


def test_without_loader_the_provider_is_disabled_and_returns_none():
    provider = ModelProvider(None)
    provider.start()
    assert not provider.enabled and provider.get() is None


def test_loads_in_background_and_retries_until_it_works():
    attempts = []

    def loader():
        attempts.append(1)
        if len(attempts) < 3:
            raise ConnectionError("mlflow fora do ar")
        return "modelo"

    provider = ModelProvider(loader, retry_seconds=0.01)
    assert provider.get() is None
    provider.start()
    assert wait_for(lambda: provider.get() == "modelo")
    assert len(attempts) == 3 and provider.last_error is None
    provider.stop()


def test_failure_never_raises_and_keeps_the_error():
    def loader():
        raise RuntimeError("falhou")

    provider = ModelProvider(loader, retry_seconds=0.01)
    provider.start()
    assert wait_for(lambda: provider.last_error is not None)
    assert provider.get() is None and "RuntimeError" in provider.last_error
    provider.stop()


def test_create_provider_needs_the_tracking_uri_and_can_be_turned_off():
    assert not create_provider({}).enabled
    assert not create_provider({"MLFLOW_TRACKING_URI": "http://x", "SINALIZA_USE_MODEL": "false"}).enabled
