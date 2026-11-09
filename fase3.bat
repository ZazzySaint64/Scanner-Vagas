@echo off
rem Menu da Fase 3 (harness do agente com Gemini). De dois cliques ou rode "fase3.bat".
rem Sem acentos de proposito: o cmd do Windows embaralha acentos em arquivos .bat.

cd /d "%~dp0"

:menu
echo.
echo ============ Radar de Estagios - Fase 3 (agente) ============
echo  1. Testar o harness com modelo FALSO (sem chave, sem custo)
echo  2. Abrir o .env (colar GEMINI_API_KEY, trocar modelo e limites)
echo  3. Aplicar o .env / reconstruir o agente (rode depois da opcao 2)
echo  4. Listar os modelos Gemini que a sua chave pode usar
echo  5. Avaliar uma vaga (cola no Bloco de Notas)
echo  6. Ver o trace de uma execucao (passo a passo)
echo  7. Abrir o /docs do agente no navegador
echo  0. Sair
echo =============================================================
set "op="
set /p "op=Escolha: "
if not defined op exit /b

if "%op%"=="1" goto teste
if "%op%"=="2" (
  start "" notepad "%~dp0.env"
  goto menu
)
if "%op%"=="3" goto rebuild
if "%op%"=="4" goto modelos
if "%op%"=="5" goto avaliar
if "%op%"=="6" goto trace
if "%op%"=="7" (
  start "" http://localhost:8000/docs
  goto menu
)
if "%op%"=="0" exit /b
echo Opcao invalida.
goto menu

:teste
echo.
docker compose exec -T agente python harness.py --teste
goto menu

:rebuild
docker compose up -d --build agente
goto menu

:modelos
echo.
docker compose exec -T agente python harness.py --modelos
goto menu

:avaliar
rem A vaga fica em dados\vagas\ (fora do Git e fora da indexacao do perfil).
if not exist "dados\vagas" mkdir "dados\vagas"
if not exist "dados\vagas\vaga.txt" type nul > "dados\vagas\vaga.txt"
start "" notepad "%~dp0dados\vagas\vaga.txt"
echo.
echo Cole o texto da vaga no Bloco de Notas, salve com Ctrl+S e volte aqui.
pause
set "emp="
set /p "emp=Nome da empresa: "
if not defined emp goto menu
set "link="
set /p "link=Link da vaga (Enter para pular): "
echo.
echo Avaliando... (o agente faz varias chamadas ao Gemini, pode levar ate 1 minuto)
if defined link (
  docker compose exec -T agente python harness.py dados/vagas/vaga.txt "%emp%" "%link%"
) else (
  docker compose exec -T agente python harness.py dados/vagas/vaga.txt "%emp%"
)
goto menu

:trace
echo.
set "id="
set /p "id=Numero da execucao (execucao_id): "
if not defined id goto menu
docker compose exec -T agente python harness.py --trace %id%
goto menu
