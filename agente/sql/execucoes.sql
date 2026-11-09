-- Tabelas da Fase 3 (harness). Roda a cada conexão; IF NOT EXISTS torna seguro repetir.

-- Uma linha por avaliação pedida. É o "cabeçalho" do trace.
CREATE TABLE IF NOT EXISTS execucoes (
    id             serial PRIMARY KEY,
    criado_em      timestamptz NOT NULL DEFAULT now(),
    empresa        text NOT NULL,
    link           text,
    texto_vaga     text NOT NULL,
    modelo         text NOT NULL,
    -- rodando | ok | limite_passos | limite_tempo | limite_tokens | saida_invalida | erro
    status         text NOT NULL DEFAULT 'rodando',
    erro           text,
    resultado      jsonb,
    tokens_entrada int NOT NULL DEFAULT 0,
    tokens_saida   int NOT NULL DEFAULT 0,
    duracao_ms     int
);

-- Uma linha por passo: cada chamada ao modelo e cada ferramenta executada.
-- É isto que GET /execucoes/{id} devolve, na ordem.
CREATE TABLE IF NOT EXISTS passos (
    id             serial PRIMARY KEY,
    execucao_id    int NOT NULL REFERENCES execucoes(id) ON DELETE CASCADE,
    n              int NOT NULL,           -- ordem dentro da execução
    tipo           text NOT NULL,          -- 'modelo' ou 'ferramenta'
    ferramenta     text,
    entrada        jsonb,
    saida          jsonb,
    erro           boolean NOT NULL DEFAULT false,
    tokens_entrada int,
    tokens_saida   int,
    duracao_ms     int NOT NULL
);

-- Escrita da ferramenta salvar_avaliacao. Lida pela consultar_historico.
CREATE TABLE IF NOT EXISTS avaliacoes (
    id           serial PRIMARY KEY,
    execucao_id  int NOT NULL REFERENCES execucoes(id) ON DELETE CASCADE,
    criado_em    timestamptz NOT NULL DEFAULT now(),
    empresa      text NOT NULL,
    link         text,
    nota         int NOT NULL CHECK (nota BETWEEN 0 AND 10),
    recomendacao text NOT NULL CHECK (recomendacao IN ('aplicar', 'talvez', 'ignorar')),
    avaliacao    jsonb NOT NULL
);

-- Escrita da ferramenta rascunhar_mensagem. Só um rascunho: ninguém envia nada daqui.
CREATE TABLE IF NOT EXISTS rascunhos (
    id          serial PRIMARY KEY,
    execucao_id int NOT NULL REFERENCES execucoes(id) ON DELETE CASCADE,
    criado_em   timestamptz NOT NULL DEFAULT now(),
    texto       text NOT NULL
);

-- Fase 4: impressão digital da vaga, para o cache (mesma vaga = mesma avaliação, sem gastar tokens).
ALTER TABLE execucoes ADD COLUMN IF NOT EXISTS hash_vaga text;

-- Fase 5: de onde veio a execução. 'api' = vaga real; 'avaliacao' = rodada de medição.
-- Medições não entram no cache nem no histórico que o agente consulta.
ALTER TABLE execucoes ADD COLUMN IF NOT EXISTS origem text NOT NULL DEFAULT 'api';
