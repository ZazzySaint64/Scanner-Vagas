@echo off
rem Menu dos experimentos da Fase 1. De dois cliques ou rode "fase1.bat" no terminal.
rem Sem acentos de proposito: o cmd do Windows embaralha acentos em arquivos .bat.

rem Vai para a pasta deste arquivo, onde esta o docker-compose.yml.
cd /d "%~dp0"

:menu
echo.
echo ================= Radar de Estagios - Fase 1 =================
echo  1. Estado dos servicos           (docker compose ps)
echo  2. Logs do agente ao vivo        (docker compose logs -f agente)
echo  3. Teste do "interfone"          (n8n chama agente vs localhost)
echo  4. Parar so o n8n e testar agente
echo  5. Religar o n8n
echo  6. down + up   (volumes ficam)
echo  7. down -v + up (APAGA volumes: conta do n8n e banco)
echo  8. Entrar no banco (psql)
echo  9. Subir tudo  (docker compose up -d --build)
echo  0. Sair
echo ==============================================================
set "op="
set /p "op=Escolha: "
rem Enter vazio (ou fim da entrada) sai, em vez de repetir o menu para sempre.
if not defined op exit /b

if "%op%"=="1" goto ps
if "%op%"=="2" goto logs
if "%op%"=="3" goto interfone
if "%op%"=="4" goto stopn8n
if "%op%"=="5" goto startn8n
if "%op%"=="6" goto down
if "%op%"=="7" goto downv
if "%op%"=="8" goto psql
if "%op%"=="9" goto up
if "%op%"=="0" exit /b
echo Opcao invalida.
goto menu

:ps
echo.
echo Repare: "db" mostra (healthy) por causa do healthcheck,
echo e nao tem 0.0.0.0 nas portas: o banco nao esta publicado no seu PC.
docker compose ps
goto menu

:logs
echo.
echo Abra localhost:8000/docs, chame /health e veja a linha nova aqui.
echo Para voltar ao menu: Ctrl+C e depois responda N.
docker compose logs -f agente
goto menu

:interfone
echo.
echo [A] De dentro do n8n, pelo NOME do servico: http://agente:8000/health
docker compose exec -T n8n wget -qO- http://agente:8000/health
echo.
echo [B] De dentro do n8n, por localhost: http://localhost:8000/health
docker compose exec -T n8n wget -qO- http://localhost:8000/health
echo.
echo [C] Do SEU PC, por localhost (funciona por causa do "ports: 8000:8000"):
curl -s http://localhost:8000/health
echo.
echo Pergunta: por que A e C funcionam e B falha?
goto menu

:stopn8n
echo.
docker compose stop n8n
echo Agente continua de pe? Resposta de localhost:8000/health:
curl -s http://localhost:8000/health
echo.
echo Abra localhost:5678 no navegador: o que acontece? Use a opcao 5 para religar.
goto menu

:startn8n
docker compose start n8n
goto menu

:down
echo.
echo down apaga containers e rede. Volumes (db_data, n8n_data) ficam.
docker compose down
docker compose up -d
echo Abra localhost:5678: sua conta continua la?
goto menu

:downv
echo.
echo ATENCAO: down -v apaga os volumes. Voce perde a conta do n8n,
echo os fluxos, as credenciais e tudo o que estiver no banco. Nao tem volta.
set "conf="
set /p "conf=Digite SIM para continuar: "
if not "%conf%"=="SIM" (
  echo Cancelado.
  goto menu
)
docker compose down -v
docker compose up -d
echo Abra localhost:5678: o que mudou? O 01-init.sql rodou de novo.
goto menu

:psql
echo.
echo Dentro do psql:  \dx = extensoes   \l = bancos   \q = sair
rem sh -c faz o shell do container expandir as variaveis do .env que o Compose injetou.
docker compose exec db sh -c "psql -U $POSTGRES_USER -d $POSTGRES_DB"
goto menu

:up
docker compose up -d --build
goto menu
