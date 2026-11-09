"""As ferramentas que o agente pode usar. São as "mãos" do agente.

O modelo NÃO executa nada: ele só PEDE "chame buscar_no_perfil com tal pergunta".
Quem executa é o harness, que procura o pedido neste registro. Se a ferramenta
não está aqui, ela não existe para o agente.

Cada ferramenta tem um nível de risco:
  leitura  -> só consulta (buscar_no_perfil, consultar_historico)
  escrita  -> grava no banco, com execucao_id registrado (salvar_avaliacao, rascunhar_mensagem)
NÃO existe ferramenta de envio (e-mail, mensagem, candidatura), de propósito:
o texto da vaga não é confiável e pode tentar dar ordens ao agente. Sem ferramenta
de envio, o pior que uma vaga maliciosa consegue é distorcer uma nota, e o trace mostra.
"""
from typing import Literal

from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

import perfil


# ------------------------------------------------------------- saída final
# O formato da avaliação. Quem garante o formato é o Pydantic, não o prompt:
# se o modelo mandar nota 15 ou recomendação "talvez sim", a validação falha e o
# harness devolve o erro ao modelo para ele corrigir.
class PontoForte(BaseModel):
    ponto: str = Field(min_length=3)
    evidencia: str = Field(min_length=3)  # trecho do perfil que prova o ponto


class Avaliacao(BaseModel):
    nota: int = Field(ge=0, le=10)
    pontos_fortes: list[PontoForte]
    lacunas: list[str]
    recomendacao: Literal["aplicar", "talvez", "ignorar"]
    resumo: str = Field(min_length=10, max_length=1500)


# ------------------------------------------------------------- implementações
# Toda ferramenta recebe (ctx, **argumentos) e devolve um dict.
# ctx é o contexto da execução: conexão com o banco e execucao_id.
# Erro aqui NÃO derruba o programa: o harness captura e devolve ao modelo.

def buscar_no_perfil(ctx, pergunta: str) -> dict:
    # Reaproveita a busca híbrida da Fase 2. k=3 para não encher o contexto.
    return perfil.buscar(pergunta, k=3)


def consultar_historico(ctx, empresa: str | None = None, limite: int = 5) -> dict:
    # SQL PARAMETRIZADO: o valor de "empresa" vai separado do comando (%(e)s).
    # Mesmo que a vaga convença o modelo a mandar "x'; DROP TABLE avaliacoes; --",
    # o Postgres trata isso como texto a procurar, não como comando.
    limite = max(1, min(int(limite), 20))
    linhas = ctx.conn.execute(
        """
        SELECT a.empresa, a.link, a.nota, a.recomendacao, a.criado_em::date::text
        FROM avaliacoes a JOIN execucoes x ON x.id = a.execucao_id
        -- Só avaliações reais: as rodadas de medição da Fase 5 não viram "histórico".
        WHERE x.origem = 'api'
          AND (%(e)s::text IS NULL OR a.empresa ILIKE '%%' || %(e)s || '%%')
        ORDER BY a.criado_em DESC
        LIMIT %(l)s
        """,
        {"e": empresa, "l": limite},
    ).fetchall()
    return {
        "avaliacoes": [
            {"empresa": e, "link": lk, "nota": n, "recomendacao": r, "data": d}
            for e, lk, n, r, d in linhas
        ]
    }


def rascunhar_mensagem(ctx, texto: str) -> dict:
    # Só GRAVA o rascunho. Enviar é decisão sua, fora do agente (Fase 4: aprovação no n8n).
    (rid,) = ctx.conn.execute(
        "INSERT INTO rascunhos (execucao_id, texto) VALUES (%s, %s) RETURNING id",
        (ctx.execucao_id, texto),
    ).fetchone()
    ctx.rascunho = texto
    return {"rascunho_id": rid, "aviso": "rascunho gravado, nada foi enviado"}


def salvar_avaliacao(ctx, **args) -> dict:
    # Ferramenta de FECHAMENTO: chamada com sucesso, o laço termina.
    # Valida com Pydantic ANTES de gravar; inválido levanta erro e nada é gravado.
    av = Avaliacao.model_validate(args)
    ctx.conn.execute(
        """
        INSERT INTO avaliacoes (execucao_id, empresa, link, nota, recomendacao, avaliacao)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (ctx.execucao_id, ctx.empresa, ctx.link, av.nota, av.recomendacao, Jsonb(av.model_dump())),
    )
    ctx.avaliacao = av
    return {"ok": True}


# ------------------------------------------------------------- registro
# Descrições e parâmetros (JSON Schema) que o MODELO lê para decidir o que chamar.
# A descrição é parte do "prompt": descrição vaga = ferramenta ignorada (experimento 3).
# O formato abaixo é o que o Gemini aceita em FunctionDeclaration(parameters_json_schema=...).
REGISTRO = {
    "buscar_no_perfil": {
        "risco": "leitura",
        "funcao": buscar_no_perfil,
        "descricao": (
            "Busca no perfil do candidato (currículo, projetos, habilidades). Devolve "
            "'termos' (cada palavra da pergunta aparece ou não no perfil) e 'trechos' "
            "(os 3 trechos mais relevantes). Use uma vez para cada requisito importante "
            "da vaga. É a ÚNICA fonte de evidência sobre o candidato."
        ),
        "parametros": {
            "type": "object",
            "properties": {
                "pergunta": {"type": "string", "description": "Requisito a procurar, ex.: 'experiência com Docker'"},
            },
            "required": ["pergunta"],
        },
    },
    "consultar_historico": {
        "risco": "leitura",
        "funcao": consultar_historico,
        "descricao": (
            "Lista avaliações de vagas feitas antes (empresa, nota, recomendação, data). "
            "Use para ver se a empresa já foi avaliada."
        ),
        "parametros": {
            "type": "object",
            "properties": {
                "empresa": {"type": "string", "description": "Parte do nome da empresa. Omita para listar as mais recentes."},
                "limite": {"type": "integer", "description": "Quantas linhas, de 1 a 20."},
            },
        },
    },
    "rascunhar_mensagem": {
        "risco": "escrita",
        "funcao": rascunhar_mensagem,
        "descricao": (
            "Grava um RASCUNHO de mensagem curta de apresentação para o recrutador. "
            "Não envia nada. Use só se a recomendação for 'aplicar' ou 'talvez', "
            "e só cite experiências encontradas com buscar_no_perfil."
        ),
        "parametros": {
            "type": "object",
            "properties": {"texto": {"type": "string", "description": "Mensagem em português, até 120 palavras."}},
            "required": ["texto"],
        },
    },
    "salvar_avaliacao": {
        "risco": "escrita",
        "funcao": salvar_avaliacao,
        "descricao": (
            "Grava a avaliação FINAL e encerra o trabalho. Chame uma única vez, por último. "
            "Cada ponto forte precisa de evidência copiada de um trecho do perfil."
        ),
        "parametros": {
            "type": "object",
            "properties": {
                "nota": {"type": "integer", "description": "0 a 10: quanto o perfil atende a vaga."},
                "pontos_fortes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "ponto": {"type": "string"},
                            "evidencia": {"type": "string", "description": "Frase do perfil que prova o ponto."},
                        },
                        "required": ["ponto", "evidencia"],
                    },
                },
                "lacunas": {"type": "array", "items": {"type": "string"}, "description": "Requisitos da vaga sem evidência no perfil."},
                "recomendacao": {"type": "string", "enum": ["aplicar", "talvez", "ignorar"]},
                "resumo": {"type": "string", "description": "2 a 4 frases justificando a nota."},
            },
            "required": ["nota", "pontos_fortes", "lacunas", "recomendacao", "resumo"],
        },
    },
}
