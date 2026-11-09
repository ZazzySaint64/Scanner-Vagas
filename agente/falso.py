"""Modelo FALSO: imita o cliente do Gemini com respostas combinadas de antemão.

Usado nos testes (tests/, harness.py --teste, avaliar.py --teste). Sem rede, sem
chave, sem custo, e sempre a mesma resposta: um teste que muda de resultado sozinho
não prova nada.
"""
from google.genai import types


def resp(*partes, t_in=100, t_out=20):
    """Uma resposta do 'modelo' com estas partes (texto e/ou pedidos de ferramenta)."""
    return types.GenerateContentResponse(
        candidates=[types.Candidate(content=types.Content(role="model", parts=list(partes)))],
        usage_metadata=types.GenerateContentResponseUsageMetadata(prompt_token_count=t_in, candidates_token_count=t_out),
    )


def chama(nome, **args):
    """Parte de resposta em que o 'modelo' pede uma ferramenta."""
    return types.Part.from_function_call(name=nome, args=args)


def texto(t):
    return types.Part.from_text(text=t)


class Falso:
    """Imita genai.Client: client.models.generate_content(...) devolve o roteiro em ordem.
    ciclo=False: acabou o roteiro, repete a última resposta (modelo que nunca termina).
    ciclo=True: volta ao início (cada execução consome o mesmo número de respostas).
    Guarda em 'pedidos' o histórico enviado em cada chamada, para os testes conferirem."""

    def __init__(self, *roteiro, ciclo=False):
        self.roteiro, self.ciclo, self.i, self.models, self.pedidos = roteiro, ciclo, 0, self, []

    def generate_content(self, model=None, contents=None, config=None):
        self.pedidos.append(list(contents) if isinstance(contents, list) else contents)
        n = self.i % len(self.roteiro) if self.ciclo else min(self.i, len(self.roteiro) - 1)
        self.i += 1
        return self.roteiro[n]
