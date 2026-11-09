"""Serviço "agente" do Radar de Estágios.

Fase 1: rota /health.
Fase 2: rota /perfil/buscar (RAG sobre o seu perfil).
Fase 3: harness do agente, rotas /avaliar-vaga e /execucoes/{id}.
Fase 4: chave X-API-Key em todas as rotas (menos /health) e cache por hash da vaga.

Quem roda este arquivo é o uvicorn, dentro do container, com o comando
"uvicorn main:app": "main" é este arquivo (main.py) e "app" é a variável abaixo.
"""
import os
import secrets

from fastapi import Depends, FastAPI, HTTPException, Query, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

import harness
import perfil

# O objeto que o uvicorn procura. Todas as rotas são registradas nele.
app = FastAPI(title="Radar de Estágios - agente")

# Lê o cabeçalho X-API-Key. Também cria o botão "Authorize" no /docs.
_cabecalho = APIKeyHeader(name="X-API-Key", auto_error=False)


def exigir_chave(chave: str | None = Security(_cabecalho)):
    """Porteiro: só passa quem mandar a mesma chave que está em AGENTE_API_KEY no .env."""
    esperada = os.environ.get("AGENTE_API_KEY", "")
    if not esperada:
        # Sem chave configurada, fecha tudo (mais seguro que deixar tudo aberto).
        raise HTTPException(status_code=503, detail="AGENTE_API_KEY vazia no .env")
    # compare_digest leva o mesmo tempo acerte ou erre. Um "==" comum para no 1º caractere
    # diferente, e medindo esse tempo um atacante adivinharia a chave aos poucos.
    if not chave or not secrets.compare_digest(chave.encode(), esperada.encode()):
        raise HTTPException(status_code=401, detail="X-API-Key ausente ou errada")


# Aplicado em cada rota protegida abaixo.
PROTEGIDA = [Depends(exigir_chave)]


@app.get("/health")
def health():
    # Rota de "sinal de vida", ABERTA de propósito: não revela nada e serve para checar
    # se o serviço subiu sem precisar da chave. Não toca no banco nem no Gemini:
    # se ela responde, o processo está de pé. O n8n e você (pelo /docs)
    # vão usá-la para confirmar que o serviço subiu.
    return {"status": "ok"}


@app.get("/perfil/buscar", dependencies=PROTEGIDA)
def perfil_buscar(
    q: str = Query(..., min_length=2, description="Pergunta em linguagem natural, ex.: 'experiência com banco de dados'"),
    k: int = Query(5, ge=1, le=20, description="Quantos trechos devolver"),
):
    # Busca híbrida (ver perfil.py): "termos" diz quais palavras da pergunta existem
    # no seu perfil; "trechos" traz os k mais relevantes, com a distância de sentido
    # (menor = mais parecido) e as palavras da pergunta que aparecem em cada um.
    return {"pergunta": q, **perfil.buscar(q, k)}


class Vaga(BaseModel):
    # Limites de tamanho na porta de entrada: texto gigante = tokens (dinheiro) jogados fora.
    texto: str = Field(min_length=50, max_length=20000, description="Texto completo da vaga, colado")
    empresa: str = Field(min_length=1, max_length=200)
    link: str | None = Field(None, max_length=500)


@app.post("/avaliar-vaga", dependencies=PROTEGIDA)
def avaliar_vaga(vaga: Vaga):
    # "def" sem "async": o FastAPI roda numa thread separada, porque o laço espera
    # o Gemini responder e não pode travar as outras rotas enquanto isso.
    # Cache: a mesma vaga já foi avaliada com sucesso por este modelo? Devolve a
    # avaliação anterior (com o execucao_id original) sem gastar nenhum token.
    anterior = harness.do_cache(vaga.texto)
    if anterior:
        # Empresa e link vêm do pedido ATUAL: a avaliação guardada pode ser antiga
        # (sem esses campos) ou ter sido pedida sem link.
        return {**anterior, "empresa": vaga.empresa, "link": vaga.link, "cache": True}
    try:
        r = harness.avaliar(vaga.texto, vaga.empresa, vaga.link)
    except harness.SemChave as e:
        raise HTTPException(status_code=503, detail=str(e))  # 503 = serviço não configurado
    if r["status"] != "ok":
        # 502 = "o serviço de que eu dependo (o modelo) não entregou". O execucao_id vai
        # junto para você abrir o trace e ver em que passo parou.
        raise HTTPException(status_code=502, detail=r)
    return {**r, "cache": False}


@app.get("/execucoes/{execucao_id}", dependencies=PROTEGIDA)
def ver_execucao(execucao_id: int):
    # O trace completo: cada chamada ao modelo e cada ferramenta, com entrada, saída, tokens e tempo.
    t = harness.execucao(execucao_id)
    if t is None:
        raise HTTPException(status_code=404, detail="execução não encontrada")
    return t
