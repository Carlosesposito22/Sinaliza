import numpy as np
import pandas as pd

from textgloss import modeling


def _words():
    n = 400
    return pd.DataFrame(
        {
            "frase_id": np.repeat(np.arange(n // 4), 4),
            "split": ["treino"] * 360 + ["teste"] * 40,
            "rotulo": np.tile([0, 1], n // 2),
        }
    )


def test_train_validation_agrupa_por_frase_e_nao_toca_no_teste():
    fit, val = modeling.train_validation(_words())
    assert set(fit["frase_id"]).isdisjoint(val["frase_id"])
    assert (fit["split"] == "treino").all() and (val["split"] == "treino").all()
    assert len(fit) + len(val) == 360


def test_evaluate_perfeito_e_pior_caso():
    y = np.array([0, 1, 0, 1])
    assert modeling.evaluate(y, y)["f1_macro"] == 1.0
    assert modeling.evaluate(y, 1 - y)["f1_macro"] == 0.0


def test_lista_fixa_descarta_palavra_funcional():
    words = pd.DataFrame({"palavra": ["de", "casa", "Que", "escola"]})
    assert list(modeling.fixed_list_predict(words)) == [0, 1, 0, 1]
