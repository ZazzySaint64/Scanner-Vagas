"""Imprime a credencial "Radar X-API-Key" no formato de importação do n8n.

Usado só pela opção "Reimportar fluxos" do fase4.bat, que passa a saída direto
para o "n8n import:credentials" por um cano (|), sem gravar a chave em arquivo
no seu PC nem mostrar na tela. O n8n criptografa a credencial ao importar.
"""
import json
import os

print(json.dumps([{
    "id": "radarApiKeyCred1",  # mesmo id usado nos JSON dos fluxos
    "name": "Radar X-API-Key",
    "type": "httpHeaderAuth",
    "data": {"name": "X-API-Key", "value": os.environ["AGENTE_API_KEY"]},
}]))
