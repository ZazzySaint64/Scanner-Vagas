"""Indexa os seus documentos de dados/ no banco.

Uso (de fora do container):  docker compose exec agente python indexar.py
Pode rodar quantas vezes quiser: o resultado é sempre o mesmo (idempotente).

Passos:
1. Lê cada .md e .txt de dados/.
2. Divide em trechos pelos títulos (#, ##, ###...), não por tamanho fixo.
3. Calcula um hash de cada trecho (impressão digital do conteúdo).
4. Apaga do banco trechos que não existem mais (você editou ou removeu a seção).
5. Gera embedding só dos trechos novos e grava.
"""
import hashlib
import sys
from pathlib import Path

PASTA = Path("/app/dados")


def dividir_markdown(texto: str, fonte: str) -> list[dict]:
    """Corta o texto em um trecho por título.

    Por que por título: no currículo, "Python, SQL, Docker" solto não diz nada.
    Dentro da seção "Projeto X: usei Python, SQL, Docker para..." vira evidência.
    Cortar por título mantém cada projeto inteiro num trecho só.
    """
    trechos = []
    titulo = fonte  # texto antes do primeiro título usa o nome do arquivo
    linhas: list[str] = []

    def fechar():
        corpo = "\n".join(linhas).strip()
        if corpo:  # seção só com título e nada embaixo não vira trecho
            # O título entra no conteúdo: ele carrega sentido ("Projeto: Chatbot").
            trechos.append({"fonte": fonte, "titulo": titulo, "conteudo": f"{titulo}\n{corpo}"})

    for linha in texto.splitlines():
        if linha.lstrip().startswith("#"):
            fechar()
            titulo = linha.lstrip("# ").strip()
            linhas = []
        else:
            linhas.append(linha)
    fechar()
    return trechos


def ler_trechos(pasta: Path, modelo: str) -> list[dict]:
    trechos = []
    for arq in sorted(pasta.glob("*")):
        if arq.suffix.lower() not in (".md", ".txt"):
            continue
        # .txt não tem títulos com #, então vira um trecho só (o arquivo inteiro).
        trechos += dividir_markdown(arq.read_text(encoding="utf-8"), arq.name)
    for t in trechos:
        # O hash inclui a fonte (o mesmo texto em dois arquivos conta duas vezes) e o
        # modelo: trocou o modelo, todo hash muda, e a indexação refaz tudo sozinha.
        # Sem isso, o banco misturaria vetores de dois modelos, que não são comparáveis.
        t["hash"] = hashlib.sha256(f"{modelo}\n{t['fonte']}\n{t['conteudo']}".encode()).hexdigest()
    return trechos


def main():
    from perfil import MODELO, conectar, embeddings  # import aqui: o --teste roda sem banco nem modelo

    if not PASTA.exists():
        sys.exit(f"Pasta {PASTA} não encontrada. Crie a pasta dados/ no projeto e coloque seus .md nela.")
    trechos = ler_trechos(PASTA, MODELO)
    hashes = [t["hash"] for t in trechos]

    with conectar() as conn:
        # Tudo daqui até o fim do "with" é uma transação: ou grava tudo, ou nada.
        apagados = conn.execute(
            "DELETE FROM trechos_perfil WHERE NOT (hash = ANY(%s::text[]))", (hashes,)
        ).rowcount
        existentes = {h for (h,) in conn.execute("SELECT hash FROM trechos_perfil").fetchall()}
        novos = [t for t in trechos if t["hash"] not in existentes]

        if novos:
            print(f"Gerando embeddings de {len(novos)} trechos (a primeira vez baixa o modelo)...")
            vetores = embeddings([t["conteudo"] for t in novos], "trecho")
            for t, v in zip(novos, vetores):
                conn.execute(
                    "INSERT INTO trechos_perfil (fonte, titulo, conteudo, hash, embedding) "
                    "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (hash) DO NOTHING",
                    (t["fonte"], t["titulo"], t["conteudo"], t["hash"], v),
                )
        # Preenche a coluna da busca por palavra de TODOS os trechos (novos e antigos).
        # É barato e idempotente: o mesmo texto gera sempre as mesmas palavras.
        from perfil import TSV
        conn.execute(f"UPDATE trechos_perfil SET busca = {TSV.format('conteudo')}")
        total = conn.execute("SELECT count(*) FROM trechos_perfil").fetchone()[0]

    print(f"Arquivos lidos: {len({t['fonte'] for t in trechos})}")
    print(f"Trechos novos: {len(novos)} | removidos: {apagados} | já existiam: {len(trechos) - len(novos)}")
    print(f"Total no banco: {total}")
    for t in novos:
        print(f"  + [{t['fonte']}] {t['titulo']}")


def teste():
    """Checagem rápida do corte por títulos: python indexar.py --teste"""
    md = "intro solta\n# Projeto A\nusei Python\n## Vazio\n## Projeto B\nusei SQL\n"
    t = dividir_markdown(md, "cv.md")
    assert [x["titulo"] for x in t] == ["cv.md", "Projeto A", "Projeto B"], t
    assert t[1]["conteudo"] == "Projeto A\nusei Python"
    print("ok")


if __name__ == "__main__":
    teste() if "--teste" in sys.argv else main()
