"""Testes da porta de entrada (main.py): a chave X-API-Key e a validação do corpo."""
import pytest
from fastapi.testclient import TestClient

import main

CHAVE = "chave-de-teste"


@pytest.fixture
def cliente(monkeypatch):
    monkeypatch.setenv("AGENTE_API_KEY", CHAVE)
    return TestClient(main.app)


def test_health_e_aberta(cliente):
    assert cliente.get("/health").status_code == 200


@pytest.mark.parametrize("cabecalhos", [{}, {"X-API-Key": "errada"}])
def test_rota_protegida_recusa_sem_a_chave_certa(cliente, cabecalhos):
    assert cliente.get("/execucoes/1", headers=cabecalhos).status_code == 401


def test_rota_protegida_aceita_a_chave_certa(cliente):
    r = cliente.get("/execucoes/999999999", headers={"X-API-Key": CHAVE})
    assert r.status_code == 404  # passou pelo porteiro; a execução é que não existe


def test_sem_chave_configurada_fecha_tudo(monkeypatch):
    monkeypatch.delenv("AGENTE_API_KEY", raising=False)
    r = TestClient(main.app).get("/execucoes/1", headers={"X-API-Key": "qualquer"})
    assert r.status_code == 503


def test_vaga_curta_demais_e_recusada(cliente):
    r = cliente.post("/avaliar-vaga", headers={"X-API-Key": CHAVE}, json={"texto": "curto", "empresa": "X"})
    assert r.status_code == 422
