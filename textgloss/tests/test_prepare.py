import pandas as pd

from textgloss import prepare


def _df():
    return pd.DataFrame(
        {
            "frase_id": range(6),
            "texto": ["a", "a", "", "b", "c", "d"],
            "glosa": ["A", "A", "X", "[PONTO]", "C", "D"],
            "governo": [True, True, False, False, False, True],
        }
    )


def test_clean_remove_vazias_duplicadas_e_glosa_sem_sinal():
    out, report = prepare.clean(_df())
    assert list(out["texto"]) == ["a", "c", "d"]
    assert report["linhas_entrada"] == 6
    assert report["apos_remover_glosa_sem_sinal"] == 3


def test_split_nao_separa_palavras_da_mesma_frase_e_e_reprodutivel():
    df = pd.DataFrame({"frase_id": range(200), "governo": [i % 2 == 0 for i in range(200)]})
    a = prepare.split_by_sentence(df)
    b = prepare.split_by_sentence(df)
    assert a.equals(b)
    assert (a == "teste").sum() == 20
    assert set(a) == {"treino", "teste"}
