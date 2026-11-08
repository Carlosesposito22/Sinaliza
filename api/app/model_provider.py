"""Entrega o classificador T1 (ML nosso) à API sem nunca derrubá-la.

O modelo registrado no MLflow tem centenas de MB e leva dezenas de segundos para carregar; o MLflow
também pode subir depois da API. Por isso o carregamento roda numa thread própria, repetindo a cada
`retry_seconds` até dar certo. Enquanto não há modelo, `get()` devolve `None` e a API usa a lista fixa
(`model_version: "lista-fixa"`).
"""
import ctypes
import gc
import logging
import threading
from collections.abc import Callable
from typing import Any

logger = logging.getLogger("sinaliza.model")


def release_memory() -> None:
    """Devolve ao sistema a memória do pico de desserialização (o modelo chega a ~2,8 GB e fica com ~1 GB).

    Sem isto a glibc mantém o pico e a API ocupa o dobro do necessário. Só tem efeito no Linux.
    """
    gc.collect()
    try:
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except (OSError, AttributeError):
        pass


class ModelProvider:
    def __init__(self, loader: Callable[[], Any] | None, retry_seconds: float = 30.0):
        self._loader = loader
        self._retry_seconds = retry_seconds
        self._model: Any | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._first_attempt_done = threading.Event()
        self.last_error: str | None = None

    @property
    def enabled(self) -> bool:
        return self._loader is not None

    def start(self) -> None:
        if self._loader is None or self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="carrega-modelo", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    @property
    def settled(self) -> bool:
        """True quando a primeira tentativa de carregar terminou (com ou sem sucesso) ou o modelo está desligado.

        É o que o `/ready` e o healthcheck do compose usam: a API só "fica pronta" depois do pico de memória da
        carga, e uma máquina sem modelo registrado também fica pronta (atende com a lista fixa).
        """
        return self._loader is None or self._first_attempt_done.is_set()

    def get(self) -> Any | None:
        """O classificador carregado, ou `None` se ainda não há (a API usa a lista fixa)."""
        return self._model

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self._model = self._loader()
            except Exception as error:  # qualquer falha (rede, MLflow, versão) cai no plano B
                self.last_error = f"{type(error).__name__}: {error}"
                self._first_attempt_done.set()
                logger.warning("modelo indisponível (%s); usando a lista fixa e tentando de novo em %ss",
                               self.last_error, self._retry_seconds)
                self._stop.wait(self._retry_seconds)
                continue
            self.last_error = None
            release_memory()
            self._first_attempt_done.set()
            logger.info("modelo carregado: %s", getattr(self._model, "version", "?"))
            return


def create_provider(environ: dict[str, str]) -> ModelProvider:
    """Só carrega o modelo se `MLFLOW_TRACKING_URI` estiver definida e o pacote `textgloss` existir."""
    uri = environ.get("MLFLOW_TRACKING_URI")
    if not uri or environ.get("SINALIZA_USE_MODEL", "true").lower() == "false":
        return ModelProvider(None)
    try:
        from textgloss import infer
    except ImportError as error:
        logger.warning("textgloss indisponível (%s); a API usa a lista fixa", error)
        return ModelProvider(None)
    version = environ.get("SINALIZA_MODEL_VERSION")

    def load():
        return infer.load_from_mlflow(
            tracking_uri=uri,
            name=environ.get("SINALIZA_MODEL_NAME", infer.MODEL_NAME),
            version=int(version) if version else None,
            cache_dir=environ.get("SINALIZA_MODEL_CACHE"),
        )

    return ModelProvider(load)
