from sinaliza_mock.grading import exam_score, grade_answer, normalize

# Formas aceitas no formato do Content.accept_table (glosas do vocabulário curado).
ACCEPT = {
    "CRIANÇA": ["criança", "crianças"],
    "QUER": ["querer", "quer", "quero"],
    "IR": ["ir", "vou", "vai"],
    "BANHEIRO": ["banheiro"],
    "DOENTE": ["doente"],
    "DORMIR": ["dormir"],
    "DOR DE CABEÇA": ["dor de cabeça"],
}
FRASE = ["CRIANÇA", "QUER", "IR", "BANHEIRO"]


def test_normaliza_maiusculas_e_acentos():
    assert normalize("Mãe CABEÇA") == "mae cabeca"


def test_frase_certa_com_pontuacao_e_sem_acento_vale_um():
    grade = grade_answer("a crianca QUER ir ao banheiro!", FRASE, ACCEPT, "A criança quer ir ao banheiro.")
    assert grade.score == 1 and all(s.correct for s in grade.signs) and grade.extra_words == []


def test_ordem_nao_importa_e_formas_aceitas_valem():
    assert grade_answer("banheiro, criança, eu quero, vou", FRASE, ACCEPT).score == 1


def test_nota_parcial_por_sinal():
    grade = grade_answer("criança quer", FRASE, ACCEPT)
    assert grade.score == 0.5 and [s.correct for s in grade.signs] == [True, True, False, False]


def test_palavra_que_sobra_conta_como_erro():
    sign = grade_answer("criança escola", ["CRIANÇA"], ACCEPT, "criança")
    assert sign.score == 0.5 and sign.extra_words == ["escola"]


def test_palavra_da_frase_sem_sinal_nao_penaliza():
    grade = grade_answer("O doente precisa dormir", ["DOENTE", "DORMIR"], ACCEPT, "O doente precisa dormir.")
    assert grade.score == 1


def test_cada_palavra_vale_um_sinal_so():
    grade = grade_answer("criança", ["CRIANÇA", "CRIANÇA"], ACCEPT)
    assert [s.correct for s in grade.signs] == [True, False]


def test_forma_de_varias_palavras_tem_prioridade():
    grade = grade_answer("dor de cabeca", ["DOR DE CABEÇA"], ACCEPT)
    assert grade.score == 1 and grade.extra_words == []


def test_resposta_vazia_vale_zero():
    assert grade_answer("", FRASE, ACCEPT).score == 0


def test_nota_da_prova_e_a_media():
    assert exam_score([1, 0.5, 0]) == 0.5 and exam_score([]) == 0
