"""Testes da avaliação (Fase 5): leitura dos casos, medidas, ancoragem e relatórios.

Uma medida errada engana mais que nenhuma medida. Três bugs reais da Fase 5
viraram teste aqui: recuperação inflada pela lista de termos, "CI/CD" partido
em "CD" e datas ("dezembro/2027") contadas como tecnologia.
"""
import json
from pathlib import Path

import avaliar
import perfil
from falso import Falso, chama, resp, texto

AV = {"nota": 5, "pontos_fortes": [{"ponto": "Docker", "evidencia": "Usa Docker, escreve testes automatizados"}],
      "lacunas": ["Kubernetes"], "recomendacao": "talvez", "resumo": "Atende parte dos requisitos."}


def test_termos_tecnicos():
    assert avaliar.termos_tecnicos("Contato com Python, APIs, AWS/infraestrutura e IA (LLMs)") == \
        ["Python", "APIs", "AWS/infraestrutura", "IA", "LLMs"]
    assert avaliar.termos_tecnicos("Experiência com Node.js e C#") == ["Node.js", "C#"]
    assert avaliar.termos_tecnicos("Formatura em 2027, cursando o 2º ano") == []


def test_contem_compara_palavra_inteira():
    assert avaliar.contem("Experiência com IA e dados", "IA")
    assert not avaliar.contem("Experiência em Python", "IA")  # "ia" dentro de "experiência"


def test_lista_de_termos_nao_conta_como_recuperado():
    saida = {"termos": [{"termo": "Node.js", "aparece_no_perfil": False}], "trechos": [{"conteudo": "React"}]}
    assert not avaliar.contem(" ".join(avaliar.textos(avaliar.so_trechos(saida))), "Node.js")


def test_ancoragem(trecho_no_banco):
    buscado = "Usa Docker, escreve testes automatizados"
    with perfil.conectar() as conn:
        assert avaliar.sem_prova(conn, [{"ponto": "Docker", "evidencia": "usa Docker, escreve testes"}], buscado) == []
        falhas = avaliar.sem_prova(conn, [{"ponto": "Contato com AWS", "evidencia": "Usa Docker, escreve testes"}], buscado)
        assert len(falhas) == 1 and "AWS" in falhas[0]
        assert "não veio da busca" in avaliar.sem_prova(
            conn, [{"ponto": "Docker", "evidencia": "frase inventada pelo modelo"}], buscado)[0]
        assert avaliar.ausentes_no_perfil(conn, ["CI/CD", "AWS/infraestrutura", "Docker", "dezembro/2027"]) == ["AWS"]


def test_caso_sem_rotulo_para_tudo(tmp_path):
    (tmp_path / "vaga.txt").write_text("empresa: X\nrecomendacao:\n---\nTexto", encoding="utf-8")
    try:
        avaliar.carregar(pasta=tmp_path)
        assert False, "deveria ter parado"
    except SystemExit as e:
        assert "vaga.txt" in str(e)


def test_rodada_completa_agente_e_fixo(tmp_path, busca_falsa, trecho_no_banco, limpa_execucoes):
    casos_dir, saida = tmp_path / "casos", tmp_path / "relatorios"
    casos_dir.mkdir()
    (casos_dir / "vaga1.txt").write_text(
        "empresa: Teste\nrecomendacao: talvez\nnota: 4-6\nevidencias: Docker; Kubernetes\nteste_cego: sim\n---\n"
        "Estágio em backend com Docker e Kubernetes, Porto Alegre, híbrido.", encoding="utf-8")
    casos = avaliar.carregar(pasta=casos_dir)
    assert len(casos) == 4 and casos[0]["cego"] and casos[0]["evidencias"] == ["Docker", "Kubernetes"]

    agente = Falso(resp(chama("buscar_no_perfil", pergunta="Docker")), resp(chama("salvar_avaliacao", **AV)), ciclo=True)
    md, resumo, linhas = avaliar.rodar(casos, "agente", repeticoes=2, cliente=agente, pasta=saida, rotulo="teste agente")
    limpa_execucoes += [l["execucao_id"] for l in linhas]
    vaga1 = [l for l in linhas if l["caso"] == "vaga1"][0]
    assert vaga1["acertou"] and vaga1["erro_nota"] == 0 and vaga1["ancorada"]
    assert vaga1["recuperacao_pct"] == 50 and vaga1["citacao_pct"] == 50  # Docker sim, Kubernetes não
    assert resumo["acerto_cego"] == "100%" and resumo["variacao"] == "0 de 1 casos mudaram"
    assert resumo["ataques_resistidos"] == "6 de 6"  # 3 ataques x 2 rodadas; o falso não obedece

    fixo = Falso(resp(texto('["experiência com Docker"]')), resp(texto(json.dumps(AV))), ciclo=True)
    _, _, linhas2 = avaliar.rodar(casos[:1], "fixo", cliente=fixo, pasta=saida, rotulo="teste fixo")
    limpa_execucoes += [l["execucao_id"] for l in linhas2]
    assert linhas2[0]["acertou"] and linhas2[0]["passos"] == 2

    quadro = (saida / "quadro.md").read_text(encoding="utf-8")
    assert "teste agente" in quadro and "teste fixo" in quadro and Path(md).exists()
