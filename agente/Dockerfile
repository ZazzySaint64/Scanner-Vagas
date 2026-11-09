# Receita da imagem do serviço "agente".
# Cada instrução vira uma camada. O Docker reaproveita (cache) toda camada
# cujo conteúdo não mudou, então a ordem importa: o que muda pouco vem primeiro.

# Imagem base: Python 3.12 enxuto (slim = sem ferramentas extras do Debian).
FROM python:3.12-slim

# Pasta de trabalho dentro do container. Os comandos abaixo rodam aqui.
WORKDIR /app

# 0) O torch, versão só-CPU, numa camada própria: é o pacote mais pesado (~200 MB)
#    e quase nunca muda, então fica em cache para sempre.
RUN pip install --no-cache-dir torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu

# 1) Só o requirements.txt primeiro. Ele muda raramente...
COPY requirements.txt .
# 2) ...então esta camada (a lenta, que baixa pacotes) fica em cache
#    enquanto você só edita o código. --no-cache-dir deixa a imagem menor.
RUN pip install --no-cache-dir -r requirements.txt

# 3) O código por último: muda toda hora, e mudar ele não invalida o pip install.
COPY . .

# Documenta a porta que o processo escuta (quem publica de verdade é o "ports" do Compose).
EXPOSE 8000

# Processo principal do container. --host 0.0.0.0 é obrigatório: com o padrão
# 127.0.0.1 o uvicorn só aceitaria conexões de dentro do próprio container.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
