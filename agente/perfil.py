"""RAG do perfil: o que é comum à indexação (indexar.py) e à busca (rota /perfil/buscar).

A busca é HÍBRIDA, com duas metades que se completam:

1. Por SENTIDO (embedding): uma lista de 384 números que representa o sentido de
   um texto. Acha "desenvolvimento mobile" no trecho do app Android, sem palavra em
   comum. Bom para ORDENAR trechos. Ruim para dizer "isso não existe": tudo tem
   algum sentido parecido com alguma coisa.

2. Por PALAVRA (busca textual do Postgres): diz exatamente quais palavras da
   pergunta aparecem no perfil. "Kubernetes" não aparece em lugar nenhum = prova
   clara de ausência. Ruim para sinônimos ("mobile" não acha "Android").
"""
import os
import re
from functools import lru_cache
from pathlib import Path

import psycopg
from pgvector.psycopg import register_vector

# Modelo multilíngue (entende português e inglês) que gera vetores de 384 números.
# O E5 foi treinado para BUSCA: pergunta curta contra trecho longo. O modelo anterior
# (paraphrase-multilingual-MiniLM) ordenava pior: "desenvolvimento mobile" não achava o app Android.
# Se trocar o modelo, a dimensão pode mudar: ajuste vector(384) no SQL. A reindexação
# é automática, porque o nome do modelo entra no hash de cada trecho (ver indexar.py).
MODELO = os.environ.get("MODELO_EMBEDDING", "intfloat/multilingual-e5-small")

# Sobre o "limiar de distância" do roteiro: testado com o seu perfil e dois modelos,
# nenhum valor separou o que você tem do que não tem ("Kubernetes" ficava tão perto
# quanto "Docker"). Por isso a prova de presença/ausência vem da busca por palavra.

# Todos os arquivos de agente/sql/, em ordem alfabética (perfil.sql, execucoes.sql...).
# Cada um usa IF NOT EXISTS: rodar de novo é seguro e cria só o que faltar.
SQL_TABELA = "\n".join(
    p.read_text(encoding="utf-8") for p in sorted((Path(__file__).parent / "sql").glob("*.sql"))
)
_esquema_pronto = False


def conectar() -> psycopg.Connection:
    """Abre conexão com o Postgres.

    Sem argumentos, o psycopg lê sozinho PGHOST, PGUSER, PGPASSWORD e PGDATABASE,
    que o Compose injeta a partir do .env.
    """
    global _esquema_pronto
    conn = psycopg.connect()
    if not _esquema_pronto:
        # Só na PRIMEIRA conexão de cada processo. "ALTER TABLE ... IF NOT EXISTS" pede
        # trava exclusiva da tabela mesmo quando a coluna já existe: rodando a cada
        # conexão, ele ficava esperando para sempre outra conexão aberta do mesmo programa.
        # A extensão precisa existir antes do register_vector, que procura o tipo "vector".
        conn.execute(SQL_TABELA)
        conn.commit()
        _esquema_pronto = True
    register_vector(conn)
    return conn


@lru_cache(maxsize=1)
def modelo():
    """Carrega o modelo uma vez só e guarda na memória (lru_cache).

    O import fica aqui dentro de propósito: carregar o modelo leva segundos,
    e assim o /health e o resto do serviço sobem sem esperar por ele.
    Na primeira vez o modelo é baixado para o volume "modelos".
    """
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODELO)


def embeddings(textos: list[str], tipo: str):
    # O E5 exige um prefixo que diz o papel do texto: "query: " para a pergunta,
    # "passage: " para o trecho guardado. Sem ele, a qualidade da busca cai.
    prefixo = "query: " if tipo == "pergunta" else "passage: "
    # normalize_embeddings=True deixa todo vetor com tamanho 1: assim a
    # distância por cosseno compara só a DIREÇÃO, ou seja, o sentido.
    return modelo().encode([prefixo + t for t in textos], normalize_embeddings=True)


# Como o Postgres transforma um texto em palavras pesquisáveis. Usado igual dos dois
# lados (trecho e pergunta), senão "testes" de um lado não bate com "teste" do outro.
#   unaccent: tira acentos | 'portuguese': tira "de/com/e" e reduz ao radical
TSV = "to_tsvector('portuguese', unaccent({}))"
TSQ = "plainto_tsquery('portuguese', unaccent({}))"


def palavras(pergunta: str) -> list[str]:
    # Palavras da pergunta, mantendo termos técnicos como "Node.js", "C#", "CI/CD".
    # ponytail: separação simples por regex; termos compostos ("machine learning")
    # viram palavras soltas. Trocar por frases entre aspas se fizer falta.
    return [p for p in re.findall(r"[\w.#+/-]+", pergunta) if len(p) > 1]


def presenca(conn, lista: list[str]) -> list[tuple[str, bool]]:
    """Para cada palavra: (palavra, aparece em algum trecho do perfil?).
    numnode(...) > 0 descarta palavras vazias ("com", "de"), que não dizem nada.
    Usada pela busca e pela Fase 5 (checar se o agente citou algo que você não tem)."""
    return conn.execute(
        f"""
        SELECT w, EXISTS (SELECT 1 FROM trechos_perfil WHERE busca @@ {TSQ.format('w')})
        FROM unnest(%s::text[]) AS w
        WHERE numnode({TSQ.format('w')}) > 0
        """,
        (lista,),
    ).fetchall()


def buscar(pergunta: str, k: int = 5) -> dict:
    """Busca híbrida: quais palavras existem no perfil + os k trechos mais relevantes."""
    vetor = embeddings([pergunta], "pergunta")[0]
    lista = palavras(pergunta)
    with conectar() as conn:
        # 1) Cada palavra da pergunta aparece em ALGUM trecho do perfil?
        termos = presenca(conn, lista)

        # 2) Os trechos: primeiro os que têm mais palavras da pergunta, depois os de
        #    sentido mais próximo (<=> é a distância por cosseno do pgvector).
        #    %s são parâmetros: o psycopg manda os valores separados do SQL (sem SQL injection).
        #    ponytail: desempate simples; trocar por fusão de rankings (RRF) se o perfil crescer.
        linhas = conn.execute(
            f"""
            SELECT * FROM (
                SELECT fonte, titulo, conteudo,
                       embedding <=> %(v)s AS distancia,
                       ARRAY(SELECT w FROM unnest(%(p)s::text[]) AS w
                             WHERE numnode({TSQ.format('w')}) > 0 AND busca @@ {TSQ.format('w')}) AS em_comum
                FROM trechos_perfil
            ) AS t
            ORDER BY cardinality(em_comum) DESC, distancia
            LIMIT %(k)s
            """,
            {"v": vetor, "p": lista, "k": k},
        ).fetchall()

    return {
        # Prova de presença/ausência, palavra por palavra. É isto que o agente vai
        # usar para dizer "lacuna: Kubernetes" em vez de inventar.
        "termos": [{"termo": w, "aparece_no_perfil": achou} for w, achou in termos],
        "trechos": [
            {
                "fonte": fonte,
                "titulo": titulo,
                "conteudo": conteudo,
                "distancia": round(float(dist), 4),  # menor = sentido mais parecido
                "palavras_em_comum": em_comum,
            }
            for fonte, titulo, conteudo, dist, em_comum in linhas
        ],
    }


if __name__ == "__main__":
    # Busca pelo terminal (usada pela opção 2 do fase2.bat):
    #   docker compose exec agente python perfil.py "experiência com banco de dados"
    import sys

    r = buscar(" ".join(sys.argv[1:]))
    print("Palavras da pergunta no seu perfil:")
    for t in r["termos"]:
        print(f"  {'SIM' if t['aparece_no_perfil'] else 'NAO'}  {t['termo']}")
    print("Trechos (palavras em comum primeiro, depois sentido mais próximo):")
    for t in r["trechos"]:
        comum = ", ".join(t["palavras_em_comum"]) or "-"
        print(f"  {t['distancia']:.3f}  [{comum}]  {t['titulo']}")
