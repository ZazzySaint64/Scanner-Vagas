# Guia da Fase 4: n8n com aprovação humana

Os 3 fluxos e a credencial da chave do agente **já estão importados** no seu n8n.
Falta a parte que só você pode fazer: criar o bot do Telegram e ligar ele nos fluxos.

Abra o n8n em http://localhost:5678 (ou opção 2 do `fase4.bat`).

## O que já existe

| Fluxo | O que faz | Estado |
|---|---|---|
| Radar 1 - Entrada manual | Recebe a vaga num webhook, chama o agente, devolve a avaliação e passa para o fluxo 3 | publicado |
| Radar 2 - Alertas por e-mail | Lê e-mails de alerta, limpa o texto, chama o agente e passa para o fluxo 3 | **desligado** (opcional, passo 7) |
| Radar 3 - Roteamento e aprovação | Nota 7 ou mais: te avisa no Telegram e espera sua decisão. Nota menor: só registra | publicado, **falta o Telegram** |

Credencial **Radar X-API-Key** (menu Overview, aba Credentials): é a mesma chave
`AGENTE_API_KEY` do seu `.env`. O n8n usa ela nos dois sentidos: para chamar o agente
e para exigir a chave de quem chama o webhook do fluxo 1.

## Passo 1: criar o bot do Telegram

1. No Telegram, procure **@BotFather** (tem o selo azul de verificado).
2. Mande `/newbot`. Escolha um nome (ex.: Radar do Eric) e um usuário terminado em `bot` (ex.: `radar_eric_bot`).
3. O BotFather responde com um **token**, parecido com `123456789:AAH...`. É uma senha: não mande no chat comigo, nem para ninguém.
4. Abra a conversa com o seu bot novo e mande qualquer mensagem, por exemplo "oi". Sem isso, ele não pode te escrever.

## Passo 2: descobrir o seu chat id

1. No navegador do PC, abra (trocando SEU_TOKEN pelo token):
   `https://api.telegram.org/botSEU_TOKEN/getUpdates`
2. Procure `"chat":{"id":` seguido de um número, por exemplo `"chat":{"id":987654321`.
3. Esse número é o seu **chat id**. Ele não é segredo, mas guarde.

Se aparecer `"result":[]`, mande outra mensagem para o bot e recarregue a página.

## Passo 3: credencial do Telegram no n8n

1. No n8n: **Overview**, aba **Credentials**, botão **Create credential**.
2. Procure **Telegram API**, cole o token em **Access Token** e salve.
3. Renomeie para **Radar Telegram**, clicando no nome no topo da janela.

## Passo 4: ligar o Telegram no fluxo 3

1. Abra o fluxo **Radar 3 - Roteamento e aprovação**.
2. Clique duas vezes no nó **Configurar**. Troque `COLE_AQUI_O_SEU_CHAT_ID` pelo seu chat id. Feche.
3. Clique duas vezes no nó **Avisa você**. Em **Credential to connect with**, escolha **Radar Telegram**. Feche.
4. Faça o mesmo no nó **Manda o rascunho final**.
5. Clique em **Save** e depois em **Publish**, no topo. Sem publicar, o n8n continua usando a versão antiga.

## Passo 5: testar

1. `fase4.bat`, opção 1. Cole uma vaga, digite a empresa.
2. Na tela aparece a nota. Se for 7 ou mais, chega uma mensagem no Telegram com o resumo, o rascunho e um link.
3. Abra o link **no navegador do PC**. Ele aponta para `localhost`, então não abre no celular.
4. No formulário, escolha **aprovar** ou **rejeitar**. Se quiser, cole um rascunho editado. Envie.
5. Aprovou: chega uma segunda mensagem com o rascunho final. **Enviar à empresa é com você.**
6. Em **Overview**, aba **Executions**, veja cada execução e clique nela para ver os dados que passaram por cada nó.

A primeira vaga que você avaliou (MVA) está no cache: ela volta na hora, sem gastar tokens.

## Como o n8n passa dados de um nó para o outro

Cada nó entrega ao próximo uma lista de **itens**. Cada item é um JSON.
No fluxo 3, o item que chega tem `avaliacao.nota`, `avaliacao.resumo`, `rascunho_mensagem`...
Um campo é lido com uma **expressão** entre chaves duplas: `{{ $json.avaliacao.nota }}`.
Para ler um nó anterior, e não o imediatamente antes: `{{ $('Configurar').first().json.empresa }}`.

## URL de teste e URL de produção

- **Produção** (`/webhook/vaga`): é a que o `fase4.bat` usa. Só responde com o fluxo **publicado**.
- **Teste** (`/webhook-test/vaga`): só responde **enquanto** você clica em **Execute workflow** no editor do fluxo 1.
  Serve para ver os dados passando nó a nó, ao vivo, enquanto monta o fluxo.

## Passo 6: experimentos

1. **Cache**: mande a mesma vaga duas vezes (opção 1). A segunda diz "veio do CACHE (0 tokens)". No fluxo 3, a mensagem do Telegram mostra `[do cache]`.
2. **Agente parado**: opção 4, depois opção 1. O n8n responde "Error in workflow". Na aba Executions, abra a execução vermelha e leia o erro no nó **Chama o agente**. Depois, opção 5 para ligar o agente.
3. **Limiar 7 para 5**: no fluxo 3, nó **Nota alta?**, troque 7 por 5. Save, Publish. Vagas com nota 5 e 6 passam a chegar no Telegram.
4. **Rejeitar**: no formulário, escolha rejeitar. Na aba Executions, o caminho termina em **Rejeitada ou expirada** e nenhuma mensagem final é enviada.

## Passo 7 (opcional): alertas por e-mail com Gmail

O fluxo 2 lê **só** a pasta (marcador) **Radar**, nunca a caixa de entrada inteira.
Tudo o que ele ler vai para o Gemini, então nada de e-mail pessoal nessa pasta.

1. Gmail: ative a verificação em 2 etapas e crie uma **senha de app** em myaccount.google.com/apppasswords.
2. Gmail: crie um filtro para os alertas de vaga (ex.: de `jobalerts-noreply@linkedin.com`) com a ação **Aplicar o marcador: Radar**.
3. n8n: **Create credential**, escolha **IMAP**. User: seu Gmail. Password: a senha de app. Host: `imap.gmail.com`. Port: `993`. SSL/TLS: ligado.
4. Abra o fluxo **Radar 2**, nó **Lê alertas de vaga**, escolha a credencial. Save, Publish.

Limite conhecido: um e-mail com 5 vagas vira **uma** avaliação do e-mail inteiro.
O código que limpa o e-mail está em `n8n/limpar-email.js`. O teste dele é a opção 6 do `fase4.bat`.

## Se algo quebrar

- **Desfazer tudo**: `fase4.bat`, opção 7. Os fluxos voltam ao original. Depois, refaça o passo 4.
- **Plano B, montar à mão**: crie um fluxo novo e adicione os nós nesta ordem.
  - **Fluxo 1**: Webhook (POST, path `vaga`, Authentication: Header Auth com a credencial Radar X-API-Key, Respond: Using 'Respond to Webhook' node). Depois, HTTP Request (POST `http://agente:8000/avaliar-vaga`, Authentication: Generic, Header Auth, a mesma credencial, Body JSON com `texto`, `empresa` e `link` vindos de `$json.body`, Timeout 150000). Depois, Respond to Webhook (First Incoming Item). Por último, Execute Workflow (fluxo 3, sem esperar terminar).
  - **Fluxo 3**: Execute Workflow Trigger (Accept all data). Depois, Edit Fields (`telegram_chat_id`, incluir os outros campos). Depois, If (`{{ $json.avaliacao.nota }}` maior ou igual a 7). Saída true: Telegram (Send Message), Wait (On Form Submitted, campo dropdown "Decisão" com aprovar/rejeitar), If (Decisão igual a aprovar), Telegram. Saída false: No Operation.
