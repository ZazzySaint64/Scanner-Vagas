-- Consultas prontas sobre o trace (Fase 5). O fase5.bat roda este arquivo inteiro.
-- origem: 'api' = vaga real | 'avaliacao' = rodada de medição.
-- modelo: 'fixo:...' = fluxo fixo | sem prefixo = agente.

\echo '=== 1. As 10 execuções mais caras (tokens) ==='
SELECT id, origem, modelo, empresa, status, tokens_entrada + tokens_saida AS tokens,
       round(duracao_ms / 1000.0, 1) AS segundos
FROM execucoes ORDER BY tokens_entrada + tokens_saida DESC LIMIT 10;

\echo '=== 2. Execuções que NÃO terminaram ok (limites, erro, saída inválida) ==='
SELECT id, origem, modelo, empresa, status, left(coalesce(erro, ''), 80) AS erro
FROM execucoes WHERE status <> 'ok' ORDER BY id DESC LIMIT 20;

\echo '=== 3. Médias por modelo (agente x fixo) ==='
SELECT modelo, origem, count(*) AS execucoes,
       round(avg(tokens_entrada + tokens_saida)) AS tokens_medios,
       round(avg(duracao_ms) / 1000.0, 1) AS segundos_medios,
       round(avg((SELECT count(*) FROM passos p WHERE p.execucao_id = e.id AND p.tipo = 'modelo')), 1) AS chamadas_ao_modelo,
       round(100.0 * avg((status = 'ok')::int)) AS pct_ok
FROM execucoes e GROUP BY modelo, origem ORDER BY modelo, origem;

\echo '=== 4. Ferramentas: quantas vezes foram usadas e quantas deram erro ==='
SELECT ferramenta, count(*) AS usos, sum(erro::int) AS erros,
       round(avg(duracao_ms)) AS ms_medio
FROM passos WHERE tipo = 'ferramenta' GROUP BY ferramenta ORDER BY usos DESC;

\echo '=== 5. Distribuição das recomendações (só vagas reais) ==='
SELECT a.recomendacao, count(*) AS vagas, round(avg(a.nota), 1) AS nota_media
FROM avaliacoes a JOIN execucoes x ON x.id = a.execucao_id
WHERE x.origem = 'api' GROUP BY a.recomendacao ORDER BY vagas DESC;

\echo '=== 6. Últimas 10 execuções ==='
SELECT id, criado_em::timestamp(0) AS quando, origem, modelo, empresa, status,
       resultado -> 'avaliacao' ->> 'nota' AS nota
FROM execucoes ORDER BY id DESC LIMIT 10;
