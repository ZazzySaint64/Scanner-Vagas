"""Manda uma vaga para o fluxo 1 do n8n, como faria qualquer sistema externo.

Usado pela opção 1 do fase4.bat:
  python enviar_n8n.py dados/vagas/vaga.txt "Empresa" [link]

Roda DENTRO do container do agente, por isso o endereço é http://n8n:5678
(o nome do serviço no Compose), e a chave vem da variável AGENTE_API_KEY.
Só usa a biblioteca padrão do Python (urllib): não precisa instalar nada.
"""
import json
import os
import sys
import urllib.error
import urllib.request

# /webhook/... = URL de PRODUÇÃO: só responde com o fluxo publicado.
# /webhook-test/... = URL de TESTE: só responde enquanto você clica "Execute workflow" no editor.
URL = os.environ.get("N8N_WEBHOOK", "http://n8n:5678/webhook/vaga")


def main(arquivo, empresa, link=None):
    corpo = {"texto": open(arquivo, encoding="utf-8").read(), "empresa": empresa, "link": link}
    pedido = urllib.request.Request(
        URL, data=json.dumps(corpo).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", "X-API-Key": os.environ["AGENTE_API_KEY"]},
    )
    try:
        with urllib.request.urlopen(pedido, timeout=200) as r:
            resp = json.load(r)
    except urllib.error.HTTPError as e:
        # O n8n devolve o erro do fluxo aqui (ex.: agente parado, chave errada).
        print(f"O n8n respondeu erro {e.code}: {e.read().decode('utf-8', 'replace')[:500]}")
        print("Veja os detalhes em http://localhost:5678, aba Executions.")
        return
    except urllib.error.URLError as e:
        print(f"Não consegui falar com o n8n: {e.reason}")
        return
    av = resp.get("avaliacao") or {}
    print(f"Nota {av.get('nota')}/10 - {av.get('recomendacao')}"
          f" | execucao {resp.get('execucao_id')}{' | veio do CACHE (0 tokens)' if resp.get('cache') else ''}")
    print(av.get("resumo", ""))
    print()
    print("Nota alta (7 ou mais): o fluxo 3 te avisa no Telegram e espera sua decisão.")
    print("Nota baixa: fica só registrada. Acompanhe em http://localhost:5678, aba Executions.")


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        sys.exit(__doc__)
    main(*sys.argv[1:])
