@echo off
rem Menu da Fase 6 (portfolio). De dois cliques ou rode "fase6.bat".
rem Sem acentos de proposito: o cmd do Windows embaralha acentos em arquivos .bat.

cd /d "%~dp0"

:menu
echo.
echo ============ Radar de Estagios - Fase 6 (portfolio) ============
echo  1. Rodar TODOS os testes automaticos (modelo falso, sem custo)
echo  2. Testar o codigo que limpa e-mails
echo  3. Conferir segredos e dados pessoais ANTES de publicar
echo  4. Abrir o README
echo  5. Abrir o LEARNING_LOG
echo  0. Sair
echo ================================================================
set "op="
set /p "op=Escolha: "
if not defined op exit /b

if "%op%"=="1" goto testes
if "%op%"=="2" goto email
if "%op%"=="3" goto segredos
if "%op%"=="4" goto readme
if "%op%"=="5" goto log
if "%op%"=="0" exit /b
echo Opcao invalida.
goto menu

:testes
rem Os mesmos testes que o GitHub Actions roda a cada push.
docker compose exec -T agente pytest -v
goto menu

:email
node n8n\teste-limpar-email.js
goto menu

:segredos
python conferir_segredos.py
goto menu

:readme
start "" notepad "%~dp0README.md"
goto menu

:log
start "" notepad "%~dp0LEARNING_LOG.md"
goto menu
