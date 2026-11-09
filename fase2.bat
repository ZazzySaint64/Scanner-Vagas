@echo off
rem Menu dos experimentos da Fase 2 (RAG). De dois cliques ou rode "fase2.bat" no terminal.
rem Sem acentos de proposito: o cmd do Windows embaralha acentos em arquivos .bat.

cd /d "%~dp0"

:menu
echo.
echo ============ Radar de Estagios - Fase 2 (RAG) ============
echo  1. Indexar meu perfil (le dados\, grava no banco)
echo  2. Buscar no perfil (digite uma pergunta)
echo  3. Ver trechos gravados no banco
echo  4. Abrir o /docs do agente no navegador
echo  5. Abrir a pasta dados\
echo  6. Reconstruir o agente (depois de mudar codigo ou .env)
echo  0. Sair
echo ==========================================================
set "op="
set /p "op=Escolha: "
if not defined op exit /b

if "%op%"=="1" goto indexar
if "%op%"=="2" goto buscar
if "%op%"=="3" goto trechos
if "%op%"=="4" (
  start "" http://localhost:8000/docs
  goto menu
)
if "%op%"=="5" (
  start "" "%~dp0dados"
  goto menu
)
if "%op%"=="6" goto rebuild
if "%op%"=="0" exit /b
echo Opcao invalida.
goto menu

:indexar
echo.
echo Rode duas vezes seguidas: na segunda, "Trechos novos" deve ser 0.
echo A primeira vez baixa o modelo (~470 MB) e demora alguns minutos.
docker compose exec -T agente python indexar.py
goto menu

:buscar
echo.
set "q="
set /p "q=Pergunta (ex.: experiencia com banco de dados): "
if not defined q goto menu
echo.
echo SIM/NAO = a palavra aparece ou nao em algum trecho do seu perfil.
echo distancia: 0 = mesmo sentido, quanto maior mais diferente.
docker compose exec -T agente python perfil.py "%q%"
goto menu

:trechos
echo.
docker compose exec -T db sh -c "psql -U $POSTGRES_USER -d $POSTGRES_DB -c 'SELECT id, fonte, titulo, length(conteudo) AS caracteres FROM trechos_perfil ORDER BY fonte, id'"
goto menu

:rebuild
docker compose up -d --build agente
goto menu
