# model

Modelo texto → sequência de poses. Ainda não implementado; a API usa o `StubGenerator` de `api/app/generator.py`.

## Contrato

O modelo treinado deve ser embrulhado numa classe que cumpra `PoseGenerator` (`api/app/generator.py`):

```python
class PoseGenerator(Protocol):
    def to_glosses(self, text: str) -> list[str]: ...
    def generate(self, glosses: list[str]) -> PoseSequence: ...
```

e ser atribuída a `generator` em `api/app/main.py`. A saída segue [`docs/pose-format.md`](../docs/pose-format.md).

## Abordagens a decidir

1. **Texto → gloss → concatenação de sinais**: ML só na parte de texto → gloss; os movimentos vêm de um dicionário de sinais já extraídos. Exige poucos dados e é a opção mais viável para um MVP.
2. **Texto → pose, sequência a sequência**: um modelo generativo (Transformer ou similar) que gera os keypoints direto. É o caminho de "treinar um modelo" de verdade, mas precisa de muito mais pares texto/movimento do que temos hoje.

A escolha depende da fonte de dados definida em `data/README.md`.

## Avaliação

O grupo não tem fluentes em Libras. A validação do movimento gerado precisa de alguém da comunidade surda ou de um intérprete. Até lá, só métricas objetivas (erro de reconstrução contra os keypoints de referência) e revisão visual, que **não** atestam correção linguística.
