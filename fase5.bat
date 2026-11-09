@echo off
rem Menu da Fase 5 (avaliacao). De dois cliques ou rode "fase5.bat".
rem Sem acentos de proposito: o cmd do Windows embaralha acentos em arquivos .bat.

cd /d "%~dp0"

:menu
echo.
echo ============ Radar de Estagios - Fase 5 (avaliacao) ============
echo  1. Preparar os casos (abre dados\casos e o modelo de caso)
echo  2. Avaliar: AGENTE (modelo do .env)
echo  3. Avaliar: FLUXO FIXO (modelo do .env)
echo  4. Avaliar: agente, 3 vezes cada caso (mede a variacao)
echo  5. Avaliar com OUTRO modelo
echo  6. Experimento: agente SEM a ferramenta consultar_historico
echo  7. Experimento: agente com MENOS passos
echo  8. So os 3 casos de ataque
echo  9. Abrir o quadro de resultados
echo  S. Consultas SQL nos traces (mais caras, limites, medias...)
echo  T. Testar o script com modelo FALSO (sem custo)
echo  0. Sair
echo ================================================================
echo  Cada vaga custa ~5 chamadas ao Gemini. 15 vagas = ~90 chamadas.
set "op="
set /p "op=Escolha: "
if not defined op exit /b

if "%op%"=="1" goto preparar
if "%op%"=="2" goto agente
if "%op%"=="3" goto fixo
if "%op%"=="4" goto variacao
if "%op%"=="5" goto modelo
if "%op%"=="6" goto semhist
if "%op%"=="7" goto passos
if "%op%"=="8" goto ataques
if "%op%"=="9" goto quadro
if /i "%op%"=="S" goto sql
if /i "%op%"=="T" goto teste
if "%op%"=="0" exit /b
echo Opcao invalida.
goto menu

:preparar
if not exist "dados\casos" mkdir "dados\casos"
start "" "%~dp0dados\casos"
start "" notepad "%~dp0modelos\caso-modelo.txt"
echo.
echo Para cada vaga: copie o modelo para dados\casos\ com um nome (ex.: vaga01-empresa.txt),
echo preencha o cabecalho com a SUA opiniao e cole a vaga depois da linha ---.
echo Rotule ANTES de rodar o agente nela. Marque teste_cego: sim em 4 vagas.
goto menu

:agente
docker compose exec -T agente python avaliar.py
goto menu

:fixo
docker compose exec -T agente python avaliar.py --modo fixo
goto menu

:variacao
docker compose exec -T agente python avaliar.py --repeticoes 3
goto menu

:modelo
echo.
echo Modelos disponiveis: opcao 4 do fase3.bat. Ex.: gemini-3.8-flash
set "mod="
set /p "mod=Nome do modelo: "
if not defined mod goto menu
set "modo="
set /p "modo=Modo (agente ou fixo, Enter = agente): "
if not defined modo set "modo=agente"
docker compose exec -T agente python avaliar.py --modelo %mod% --modo %modo%
goto menu

:semhist
docker compose exec -T agente python avaliar.py --sem consultar_historico
goto menu

:passos
set "n="
set /p "n=Limite de passos (ex.: 3): "
if not defined n goto menu
docker compose exec -T agente python avaliar.py --passos %n%
goto menu

:ataques
docker compose exec -T agente python avaliar.py --so-ataques
goto menu

:quadro
if not exist "relatorios\quadro.md" echo Ainda nao ha resultados. Rode uma avaliacao primeiro.
if exist "relatorios\quadro.md" start "" notepad "%~dp0relatorios\quadro.md"
start "" "%~dp0relatorios"
goto menu

:sql
docker compose exec -T db sh -c "psql -U $POSTGRES_USER -d $POSTGRES_DB" < consultas\traces.sql
goto menu

:teste
docker compose exec -T agente python avaliar.py --teste
goto menu
