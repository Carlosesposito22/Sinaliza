"""Um experimento do MLflow por etapa e a trava do teste final, num MLflow local descartável (SQLite)."""
import mlflow
import pytest

from textgloss import train, validate


@pytest.fixture
def local_mlflow(tmp_path, monkeypatch):
    uri = f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"
    monkeypatch.setattr(train, "TRACKING_URI", uri)
    mlflow.set_tracking_uri(uri)
    yield mlflow.MlflowClient(uri)


def test_each_stage_has_its_own_experiment_with_a_description(local_mlflow):
    for stage in train.STAGES:
        train.use_experiment(stage)
    names = sorted(e.name for e in local_mlflow.search_experiments() if e.name != "Default")
    assert names == [
        "sinaliza-t1-01-baseline", "sinaliza-t1-02-comparacao-de-modelos",
        "sinaliza-t1-03-otimizacao-de-hiperparametros", "sinaliza-t1-04-validacao-e-teste-final",
    ]
    baseline = local_mlflow.get_experiment_by_name("sinaliza-t1-01-baseline")
    assert "Regressão Logística" in baseline.tags["mlflow.note.content"]
    assert len(train.experiment_ids()) == 4 and len(train.experiment_ids("baseline", "comparacao")) == 2


def test_experiment_ids_ignores_stages_that_never_ran(local_mlflow):
    train.use_experiment("baseline")
    assert len(train.experiment_ids()) == 1


def test_final_test_guard_finds_the_run_in_the_validation_experiment(local_mlflow):
    train.use_experiment("baseline")
    assert not validate.teste_final_executado()
    train.use_experiment("validacao")
    with mlflow.start_run():
        mlflow.set_tag("etapa", "teste-final")
    assert validate.teste_final_executado()


def test_final_test_guard_also_looks_at_the_old_single_experiment(local_mlflow):
    mlflow.set_experiment(train.LEGACY_EXPERIMENT)
    with mlflow.start_run():
        mlflow.set_tag("etapa", "teste-final")
    assert validate.teste_final_executado()


def test_latest_runs_reads_baseline_and_comparison_together(local_mlflow):
    for stage, name in (("baseline", "lista-fixa"), ("comparacao", "knn")):
        train.use_experiment(stage)
        with mlflow.start_run():
            mlflow.set_tag("modelo", name)
    assert set(train.latest_runs()) == {"lista-fixa", "knn"}
