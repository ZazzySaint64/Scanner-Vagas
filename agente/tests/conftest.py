"""Peças compartilhadas pelos testes. O pytest carrega este arquivo sozinho.

Os testes rodam em dois lugares:
  - no seu PC, dentro do container (fase6.bat), com o banco de verdade;
  - no GitHub Actions, com um Postgres vazio e SEM o modelo de embeddings (470 MB).
Por isso a busca no perfil é trocada por uma falsa: o que se testa aqui é o laço,
os limites e as medidas, não a qualidade da busca (essa foi medida na Fase 5).
"""
import pytest

import perfil

TRECHO = ("Usa Docker, escreve testes automatizados e mantém pipelines de CI/CD no GitHub Actions. "
          "Python com FastAPI e PostgreSQL.")
MARCA = "Empresa Teste (pytest)"


@pytest.fixture
def busca_falsa(monkeypatch):
    """Troca perfil.buscar por uma versão que sempre devolve o mesmo trecho."""
    def buscar(pergunta, k=3):
        return {"termos": [{"termo": pergunta, "aparece_no_perfil": True}],
                "trechos": [{"fonte": "perfil.md", "titulo": "Resumo", "conteudo": TRECHO,
                             "distancia": 0.1, "palavras_em_comum": []}]}
    monkeypatch.setattr(perfil, "buscar", buscar)


@pytest.fixture
def trecho_no_banco():
    """Um trecho de perfil de teste na tabela, para a checagem "existe no perfil?"
    funcionar também no banco vazio do GitHub. Apagado no fim."""
    vetor = "[" + ",".join(["0.01"] * 384) + "]"
    with perfil.conectar() as conn:
        conn.execute(
            """INSERT INTO trechos_perfil (fonte, titulo, conteudo, hash, embedding, busca)
               VALUES ('pytest', 'teste', %s, 'pytest-fixture', %s::vector,
                       to_tsvector('portuguese', unaccent(%s)))
               ON CONFLICT (hash) DO NOTHING""",
            (TRECHO, vetor, TRECHO),
        )
    yield
    with perfil.conectar() as conn:
        conn.execute("DELETE FROM trechos_perfil WHERE hash = 'pytest-fixture'")


@pytest.fixture
def limpa_execucoes():
    """Guarda os execucao_id criados no teste e apaga tudo no fim (CASCADE leva passos etc.)."""
    ids = []
    yield ids
    with perfil.conectar() as conn:
        conn.execute("DELETE FROM execucoes WHERE id = ANY(%s) OR empresa = %s", (ids, MARCA))
