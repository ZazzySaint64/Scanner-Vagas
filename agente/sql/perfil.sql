-- Tabela do RAG do perfil. Roda toda vez que o agente sobe e toda vez que você indexa.
-- "IF NOT EXISTS" torna isso seguro: na segunda vez não faz nada.
--
-- Por que não ficou em db/init/? Aqueles scripts só rodam com o banco vazio
-- (primeira subida). Seu banco já existe, então eles não rodariam de novo.

CREATE EXTENSION IF NOT EXISTS vector;
-- unaccent tira acentos: "experiência" e "experiencia" viram a mesma palavra na busca.
CREATE EXTENSION IF NOT EXISTS unaccent;

CREATE TABLE IF NOT EXISTS trechos_perfil (
    id         serial PRIMARY KEY,
    fonte      text NOT NULL,          -- nome do arquivo de origem, ex.: perfil.md
    titulo     text NOT NULL,          -- título da seção, ex.: "Projeto: Discipliner"
    conteudo   text NOT NULL,          -- o texto do trecho, que o agente vai ler
    hash       text NOT NULL UNIQUE,   -- impressão digital do trecho; UNIQUE impede duplicar
    embedding  vector(384) NOT NULL,   -- 384 = tamanho do vetor do modelo. Trocou o modelo? Muda aqui e reindexa.
    criado_em  timestamptz NOT NULL DEFAULT now()
);

-- Busca por PALAVRA (a outra metade da busca híbrida). Um tsvector é a lista das
-- palavras do trecho já "normalizadas": sem acento, sem palavras vazias ("de", "com")
-- e reduzidas ao radical ("testes", "testar" -> "test"). Quem preenche é o indexar.py.
-- ADD COLUMN IF NOT EXISTS: acrescenta a coluna numa tabela que já existia.
ALTER TABLE trechos_perfil ADD COLUMN IF NOT EXISTS busca tsvector;

-- ponytail: sem índices (HNSW no vetor, GIN no tsvector). Com dezenas de trechos,
-- comparar com todos leva milissegundos. Crie só se passar de dezenas de milhares de linhas.
