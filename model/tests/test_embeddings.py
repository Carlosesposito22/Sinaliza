import numpy as np
import torch

from sinaliza_model.data import load_vocabulary
from sinaliza_model.embeddings import (
    checkpoint_embeddings,
    cosine_similarity,
    embedding_vs_motion,
    gloss_embeddings,
    motion_distances,
    nearest_neighbors,
    spearman,
)
from sinaliza_model.network import MotionGenerator
from sinaliza_model.synthetic import make_synthetic
from sinaliza_model.train import DEFAULT_VOCABULARY, train_model


def test_gloss_embeddings_are_the_models_embedding_matrix():
    model = MotionGenerator(5, seq_len=8, hidden=16)
    vectors = gloss_embeddings(model)
    assert vectors.shape == (5, 16)
    np.testing.assert_array_equal(vectors[2], model.embedding.weight[2].detach().numpy())


def test_nearest_neighbors_excludes_self_and_orders_by_similarity():
    vectors = np.array([[1.0, 0.0], [0.9, 0.1], [0.0, 1.0], [-1.0, 0.0]])
    result = nearest_neighbors(vectors, ["A", "B", "C", "D"], k=2)
    assert [g for g, _ in result["A"]] == ["B", "C"]
    assert result["A"][0][1] > result["A"][1][1]
    assert all(g != "A" for g, _ in result["A"])
    np.testing.assert_allclose(np.diag(cosine_similarity(vectors)), 1.0)


def test_spearman_handles_monotonic_inverse_ties_and_constants():
    x = np.array([1.0, 2.0, 3.0, 4.0])
    assert spearman(x, x**3) == 1.0
    assert spearman(x, -x) == -1.0
    assert not np.isnan(spearman(np.array([1.0, 1.0, 2.0, 3.0]), x))
    assert np.isnan(spearman(np.ones(4), x))


def test_embedding_distance_tracks_motion_distance_on_synthetic_data(tmp_path):
    glosses = load_vocabulary(DEFAULT_VOCABULARY)[:20]
    samples = make_synthetic(glosses, signers=2, repetitions=2)
    model, _ = train_model(samples, glosses, seq_len=16, epochs=30)

    distances = motion_distances(samples, glosses, seq_len=16)
    assert distances.shape == (20, 20)
    np.testing.assert_allclose(distances, distances.T)
    assert (np.diag(distances) == 0).all()

    rho = embedding_vs_motion(gloss_embeddings(model), distances)
    assert -1.0 <= rho <= 1.0

    path = tmp_path / "model.pt"
    torch.save({"state_dict": model.state_dict(), "glosses": glosses, "seq_len": 16}, path)
    loaded_glosses, loaded = checkpoint_embeddings(path)
    assert loaded_glosses == glosses
    np.testing.assert_array_equal(loaded, gloss_embeddings(model))
