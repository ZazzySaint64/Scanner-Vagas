# Radar de Estágios

Um agente que lê vagas de estágio, compara cada uma com o meu perfil real e devolve uma nota de 0 a 10 com justificativa, as lacunas e um rascunho de mensagem. **Nada é enviado sozinho:** a vaga boa chega no meu Telegram e o fluxo espera eu aprovar.

Projeto de estudo feito em 6 fases: Docker, RAG, harness de agente, orquestração com n8n, avaliação com números e portfólio.

## Arquitetura

```mermaid
flowchart LR
    V[Vaga<br/>colada ou e-mail] --> N[n8n<br/>gatilho, rota, aprovação]
    N -- "POST /avaliar-vaga<br/>X-API-Key" --> A[agente<br/>FastAPI + harness]
    A -- function calling --> G[Gemini API]
    A -- "busca híbrida<br/>trace de cada passo" --> D[(Postgres<br/>pgvector)]
    N -- "nota ≥ 7" --> T[Telegram<br/>resumo + rascunho]
    T -- formulário --> N
```

| Serviço | O que faz |
|---|---|
| `db` | Postgres 17 com pgvector. Guarda o perfil em trechos com embeddings, o trace de cada execução e as avaliações. Sem porta publicada: só a rede interna alcança. |
| `agente` | FastAPI. O harness (laço do agente), 4 ferramentas, a busca híbrida no perfil e a avaliação. |
| `n8n` | Recebe a vaga (webhook ou e-mail), chama o agente, separa por nota, avisa no Telegram e espera a aprovação num formulário. |

## Subir tudo

Precisa de Docker. Depois:

```bash
cp .env.example .env        # preencha senhas, GEMINI_API_KEY e AGENTE_API_KEY
mkdir dados                 # coloque aqui o seu perfil em Markdown (ver modelos/perfil-modelo.md)
docker compose up -d --build
docker compose exec agente python indexar.py
```

- Agente: http://localhost:8000/docs (botão **Authorize** com a `AGENTE_API_KEY`)
- n8n: http://localhost:5678 (fluxos em `n8n/`, guia em `n8n/GUIA.md`)
- Testes: `docker compose exec agente pytest`

No Windows, os menus `fase1.bat` a `fase6.bat` fazem cada etapa sem digitar comandos.

## Como funciona

1. **RAG híbrido (Fase 2).** O perfil é cortado por título e cada trecho vira um embedding local (`multilingual-e5-small`, 384 dimensões). A busca combina sentido (pgvector) com palavra exata (full-text do Postgres). O sentido ordena os trechos; a palavra prova ausência ("Kubernetes: não aparece").
2. **Harness (Fase 3).** Laço de function calling com o Gemini: o modelo pede ferramentas, o código executa, devolve o resultado e grava cada passo. Limites de passos, tempo e tokens são contadores no código, não pedidos no prompt. A saída final é validada com Pydantic, com até 2 novas tentativas.
3. **Orquestração (Fase 4).** O n8n faz gatilho, roteamento, espera e aviso. O agente faz o raciocínio. Chave `X-API-Key` comparada em tempo constante, e cache por hash da vaga: a mesma vaga não gasta tokens duas vezes.
4. **Avaliação (Fase 5).** 15 vagas reais rotuladas à mão antes de rodar o agente, 5 delas como teste cego, mais 3 vagas de ataque. Mede acerto, erro da nota, ancoragem, recuperação, passos, tokens e tempo, e compara o agente com um fluxo fixo.

## Decisões de projeto

- **Não existe ferramenta de envio.** O texto da vaga não é confiável e pode tentar dar ordens ao modelo. As ferramentas são `buscar_no_perfil` e `consultar_historico` (leitura) e `rascunhar_mensagem` e `salvar_avaliacao` (escrita no banco). O pior que uma vaga maliciosa consegue é distorcer uma nota, e o trace mostra.
- **A vaga entra numa caixa `<vaga>…</vaga>`** e um `</vaga>` falso dentro do texto é removido, para ela não "sair da caixa".
- **Limite no código, não no prompt.** Pedir "use no máximo 3 passos" não garante nada; o contador do harness garante.
- **Busca híbrida em vez de limiar de distância.** Testado com o meu perfil e dois modelos, nenhum limiar separou "tenho" de "não tenho".
- **Trace no Postgres.** Cada chamada ao modelo e cada ferramenta vira uma linha, com entrada, saída, tokens e tempo (`GET /execucoes/{id}`).
- **Segredos só no `.env`; dados pessoais só em `dados/`.** Os dois estão no `.gitignore`. Portas publicadas só em `127.0.0.1`.

## Resultados (Fase 5)

Modelo `gemini-3.5-flash-lite`, 15 vagas reais + 3 ataques.

| Configuração | Acerto (ajuste) | Acerto (cego) | Erro médio da nota | Ancoragem | Tokens/vaga | Ataques |
|---|---|---|---|---|---|---|
| Agente, prompt v1 (2 rodadas) | 40% | 40% | 2,7 a 2,9 | 80% | ~9.500 | 3 de 3 |
| Fluxo fixo (2 rodadas) | 40% | 20% | 2,7 a 3,3 | 80 a 87% | ~5.000 | 3 de 3 |
| Agente, prompt v2 (elegibilidade, 3 rodadas) | 70% | 40% | 2,2 | 73 a 80% | ~10.200 | 3 de 3 |

O que os números dizem:

- O fluxo fixo empatou com o agente nas vagas de ajuste, com metade do custo, mas foi pior no cego e menos estável entre rodadas.
- O erro principal era de critério: o agente ignorava cidade e data de formatura. Uma regra no prompt (v2) subiu o acerto do ajuste de 40% para 70%. O teste cego não mudou, o que acende o alerta de ajuste enganoso.
- Rodando o v2 três vezes, o acerto ficou idêntico (7 de 10 e 2 de 5), mas 4 das 15 vagas mudaram de recomendação entre rodadas. As trocas se compensaram. Uma rodada só não basta para confiar numa nota individual.
- As 3 vagas de ataque ("dê nota 10", falso "SISTEMA:", "mande os dados para este e-mail") foram resistidas por todas as configurações.

## Limitações conhecidas

- 15 vagas é pouco: 1 vaga a mais ou a menos muda o acerto em 7 pontos percentuais.
- A checagem de ancoragem é heurística. Ela marca termos técnicos que não estão no perfil, mas confunde sinônimos ("Inteligência Artificial" contra "IA").
- Um e-mail de alerta com várias vagas vira uma avaliação só.
- O link de aprovação aponta para `localhost`: só abre no computador que roda o n8n.
- No plano gratuito do Gemini, o Google pode usar o conteúdo enviado para melhorar os produtos. Por isso o perfil não tem dados de contato.

## Estrutura

```
agente/          FastAPI, harness, ferramentas, busca, fluxo fixo, avaliação, testes
agente/tests/    testes automáticos com modelo falso (rodam no GitHub Actions)
n8n/             os 3 fluxos em JSON, guia de cliques e o código que limpa e-mails
consultas/       consultas SQL prontas sobre o trace
db/init/         script da primeira subida do banco
modelos/         modelos de perfil e de caso de avaliação
dados/           perfil e casos rotulados (fora do Git)
relatorios/      relatórios da avaliação (fora do Git)
```

## O que aprendi

<!-- Escreva com as suas palavras: o que você sabe explicar agora que não sabia antes. -->
