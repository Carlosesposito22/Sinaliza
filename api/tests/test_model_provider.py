import threading
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
    assert provider.settled  # desligado: não há o que esperar


def test_settled_after_the_first_attempt_even_if_it_fails():
    release = threading.Event()

    def loader():
        release.wait(2)
        raise LookupError("o modelo sinaliza-t1 não tem nenhuma versão registrada")

    provider = ModelProvider(loader, retry_seconds=5)
    provider.start()
    assert not provider.settled  # carregando
    release.set()
    assert wait_for(lambda: provider.settled)
    assert provider.get() is None  # sem modelo, mas pronta (atende com a lista fixa)
    provider.stop()


def test_settled_after_a_successful_load():
    provider = ModelProvider(lambda: "modelo", retry_seconds=0.01)
    provider.start()
    assert wait_for(lambda: provider.settled and provider.get() == "modelo")


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
