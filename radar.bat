@echo off
rem Liga e desliga o Radar de Estagios. De dois cliques.
rem Sem acentos de proposito: o cmd do Windows embaralha acentos em arquivos .bat.

cd /d "%~dp0"

:menu
echo.
echo ================== Radar de Estagios ==================
echo  1. LIGAR     (abre o Docker se precisar e sobe tudo)
echo  2. DESLIGAR  (para tudo e fecha o Docker: libera a RAM)
echo  3. Ver se esta rodando
echo  0. Sair
echo =======================================================
set "op="
set /p "op=Escolha: "
if not defined op exit /b
if "%op%"=="1" goto ligar
if "%op%"=="2" goto desligar
if "%op%"=="3" goto status
if "%op%"=="0" exit /b
goto menu

:ligar
docker info >nul 2>&1
if not errorlevel 1 goto subir
echo Abrindo o Docker Desktop, pode levar 1 a 2 minutos...
docker desktop start >nul 2>&1
if errorlevel 1 start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
set /a tent=0
:espera_docker
docker info >nul 2>&1
if not errorlevel 1 goto subir
set /a tent+=1
if %tent% geq 36 (
  echo O Docker nao abriu em 3 minutos. Abra o Docker Desktop na mao e tente de novo.
  goto menu
)
ping -n 6 127.0.0.1 >nul
goto espera_docker

:subir
echo Subindo banco, agente e n8n...
docker compose up -d
if errorlevel 1 (
  echo Deu erro ao subir. Leia a mensagem acima.
  goto menu
)
echo Esperando o agente ficar pronto...
set /a tent=0
:espera_agente
curl -sf -o NUL http://127.0.0.1:8000/health
if not errorlevel 1 goto pronto
set /a tent+=1
if %tent% geq 36 (
  echo O agente nao respondeu em 3 minutos. Veja o log com: docker compose logs agente
  goto menu
)
ping -n 6 127.0.0.1 >nul
goto espera_agente

:pronto
echo.
echo PRONTO. O Radar esta rodando. Pode fechar esta janela: ele continua ligado.
echo   n8n:    http://localhost:5678
echo   agente: http://localhost:8000/docs
echo Para desligar, abra este arquivo de novo e escolha 2.
goto menu

:desligar
docker info >nul 2>&1
if errorlevel 1 (
  echo O Docker ja esta desligado.
  goto menu
)
echo Parando banco, agente e n8n. Seus dados ficam guardados...
docker compose stop
echo Fechando o Docker Desktop para liberar a RAM...
docker desktop stop >nul 2>&1
echo DESLIGADO.
goto menu

:status
docker info >nul 2>&1
if errorlevel 1 (
  echo DESLIGADO: o Docker nao esta aberto.
  goto menu
)
docker compose ps --format "table {{.Service}}\t{{.Status}}"
goto menu
