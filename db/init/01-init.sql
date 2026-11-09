-- Roda uma única vez, na primeira subida do banco (volume db_data vazio).
-- Conectado ao banco definido em POSTGRES_DB (o banco do agente).

-- Habilita o pgvector neste banco: adiciona o tipo "vector" e os operadores
-- de distância usados na Fase 2. Confira depois com \dx dentro do psql.
CREATE EXTENSION IF NOT EXISTS vector;

-- Banco separado para o n8n. Cada um cuida das próprias tabelas:
-- um "down -v" ou uma migração do n8n não encosta nos dados do agente, e vice-versa.
CREATE DATABASE n8n;
