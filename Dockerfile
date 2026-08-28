# Ambiente oficial e reproduzivel para dev/testes do Steel Indicator.
#
# Motivo: no Windows, o Smart App Control/Code Integrity do sistema bloqueia
# o carregamento da extensao nativa do pandas (pandas/_libs/index.*.pyd),
# tanto no Python global quanto em .venv local, impedindo `import pandas` e,
# por consequencia, pytest/--selftest. Docker isola esse problema sem exigir
# nenhuma alteracao de politica de seguranca do Windows.
#
# Versoes fixadas em requirements.txt (pandas==3.0.5, numpy==2.4.6, etc.) -
# sao as mesmas desde o primeiro commit que introduziu requirements.txt
# (7334e74); nao ha evidencia historica de outra combinacao estavel, entao
# nenhuma versao foi trocada aqui.
FROM python:3.11-slim

WORKDIR /app

# Instala dependencias primeiro para aproveitar o cache do Docker quando so
# o codigo (nao requirements*.txt) mudar entre builds. requirements-dev.txt
# inclui requirements.txt (-r) e acrescenta pytest, ausente do arquivo de
# producao e nao pinado em nenhum outro lugar do repositorio.
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY . .

# matplotlib nao precisa de display num container - evita a extensao
# tentar resolver um backend interativo inexistente.
ENV MPLBACKEND=Agg

# pytest.ini ja define pythonpath=src; python src/indices_setoriais.py
# tambem resolve `steel_indicator` sozinho (script roda com src/ como
# diretorio do proprio arquivo). Comando default = suite de testes; ambos
# os comandos abaixo continuam disponiveis via `docker run ... <comando>`.
CMD ["python", "-m", "pytest", "tests/", "-v"]
