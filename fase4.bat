@echo off
rem Menu da Fase 4 (n8n como orquestrador). De dois cliques ou rode "fase4.bat".
rem Sem acentos de proposito: o cmd do Windows embaralha acentos em arquivos .bat.

cd /d "%~dp0"

:menu
echo.
echo ============ Radar de Estagios - Fase 4 (n8n) ============
echo  1. Mandar uma vaga para o n8n (fluxo 1, URL de producao)
echo  2. Abrir o n8n no navegador
echo  3. Abrir o guia de cliques (n8n\GUIA.md)
echo  4. Experimento: PARAR o agente
echo  5. Ligar o agente de novo
echo  6. Testar o codigo que limpa e-mails
echo  7. Reimportar os fluxos (desfaz suas mudancas nos fluxos!)
echo  0. Sair
echo ==========================================================
set "op="
set /p "op=Escolha: "
if not defined op exit /b

if "%op%"=="1" goto enviar
if "%op%"=="2" goto abrir_n8n
if "%op%"=="3" goto guia
if "%op%"=="4" goto parar
if "%op%"=="5" goto ligar
if "%op%"=="6" goto teste_email
if "%op%"=="7" goto reimportar
if "%op%"=="0" exit /b
echo Opcao invalida.
goto menu

:abrir_n8n
start "" http://localhost:5678
goto menu

:guia
start "" notepad "%~dp0n8n\GUIA.md"
goto menu

:parar
docker compose stop agente
echo Agente parado. Mande uma vaga pela opcao 1 e leia o erro na aba Executions do n8n.
goto menu

:ligar
docker compose start agente
goto menu

:teste_email
node n8n\teste-limpar-email.js
goto menu

:enviar
if not exist "dados\vagas" mkdir "dados\vagas"
if not exist "dados\vagas\vaga.txt" type nul > "dados\vagas\vaga.txt"
start "" notepad "%~dp0dados\vagas\vaga.txt"
echo.
echo Cole o texto da vaga no Bloco de Notas, salve com Ctrl+S e volte aqui.
echo (Mesma vaga de antes? O cache devolve a avaliacao sem gastar tokens.)
pause
set "emp="
set /p "emp=Nome da empresa: "
if not defined emp goto menu
set "link="
set /p "link=Link da vaga (Enter para pular): "
echo.
rem "run --rm" cria um container descartavel so para enviar: funciona mesmo com o agente parado.
echo Enviando ao n8n... (o agente pode levar ate 1 minuto)
if defined link (
  docker compose run --rm --no-deps -T agente python enviar_n8n.py dados/vagas/vaga.txt "%emp%" "%link%"
) else (
  docker compose run --rm --no-deps -T agente python enviar_n8n.py dados/vagas/vaga.txt "%emp%"
)
goto menu

:reimportar
echo.
echo ATENCAO: volta os 3 fluxos ao original. Voce perde o chat id e a credencial
echo do Telegram escolhidos nos fluxos e precisa refazer o passo 4 do guia.
set "ok="
set /p "ok=Digite SIM para continuar: "
if /i not "%ok%"=="SIM" goto menu
rem A chave vai do agente direto para o n8n por um cano (|): nao aparece na tela.
docker compose exec -T agente python n8n_credencial.py | docker compose exec -T n8n sh -c "cat > /tmp/cred.json && n8n import:credentials --input=/tmp/cred.json; rm -f /tmp/cred.json"
for %%f in (n8n\fluxo*.json) do docker compose cp "%%f" n8n:/tmp/%%~nxf
docker compose exec -T n8n sh -c "for f in /tmp/fluxo*.json; do n8n import:workflow --input=$f; done; n8n publish:workflow --id=radarRoteamento3; n8n publish:workflow --id=radarEntradaMan1"
docker compose restart n8n
echo Pronto. Espere uns 15 segundos antes de usar o n8n.
goto menu
