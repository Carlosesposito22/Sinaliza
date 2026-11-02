from textgloss import align, corpus


def test_slug_remove_acento_e_separador():
    assert corpus.slug("CIDADÃO") == "cidadao"
    assert corpus.slug("CADASTRO_NACIONAL") == "cadastronacional"


def test_gloss_keys_remove_marcas():
    keys = corpus.gloss_keys("CASA GRANDE(+) [PONTO]")
    assert keys == {"casa", "grande"}


def test_gloss_keys_negacao_incorporada_vira_nao_e_verbo():
    assert corpus.gloss_keys("NÃO_GOSTAR") == {"nao", "gostar"}


def test_gloss_keys_direcional_e_homonimo():
    assert corpus.gloss_keys("1S_AJUDAR_2S BANCO&DINHEIRO") == {"ajudar", "banco"}


def test_gloss_keys_composto_conta_inteiro_e_por_partes():
    keys = corpus.gloss_keys("CADASTRO_NACIONAL")
    assert {"cadastronacional", "cadastro", "nacional"} <= keys


def test_gloss_marks():
    marks = corpus.gloss_marks("NÃO_GOSTAR BANCO&DINHEIRO GRANDE(+) [INTERROGAÇÃO]")
    assert marks["tem_negacao"] and marks["tem_homonimo"] and marks["tem_intensidade"]
    assert marks["tipo_frase"] == "[INTERROGAÇÃO]"
    assert marks["n_sinais"] == 3


def test_label_token_usa_lema_ou_forma():
    keys = corpus.gloss_keys("INTERESSAR CIDADÃO")
    assert align.label_token("interessado", "interessar", keys) == align.MANTER
    assert align.label_token("cidadão", "cidadão", keys) == align.MANTER
    assert align.label_token("de", "de", keys) == align.DESCARTAR


def test_label_clitico_usa_primeira_parte_do_lema():
    keys = corpus.gloss_keys("CANDIDATAR MESTRADO")
    assert align.label_token("candidatar-se", "candidatar se", keys) == align.MANTER


def test_label_numeral_por_extenso_casa_com_digito():
    keys = corpus.gloss_keys("SACERDOTE 7 ALEMANHA")
    assert align.label_token("sete", "sete", keys) == align.MANTER
    assert align.label_token("seis", "seis", keys) == align.DESCARTAR
