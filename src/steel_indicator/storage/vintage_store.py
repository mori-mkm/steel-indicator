"""Persistencia append-only, imutavel e local de vintages de PUBLICACAO
(Stage G2, ADR 0012) - o conceito D mencionado no docstring de
`manifest.py` deste mesmo pacote ("qual conjunto de collection vintages +
versao de codigo/metodologia produziu um indice publicado"), explicitamente
fora de escopo la, implementado aqui.

Uma vintage e um bundle IMUTAVEL de arquivos CSV + `manifest.json` (com
hash SHA256 de cada arquivo), identificado por um `vintage_id` ordenavel
cronologicamente (`YYYYMMDDTHHMMSSZ`, sempre UTC). So filesystem local -
sem banco, cloud, API ou locking distribuido (execucao local/single-process
nesta stage, por decisao explicita).

Generico o suficiente para servir aos produtos do repositorio (IPIA/ICCS/
ICS - CLAUDE.md) via o parametro `produto` - layout
`<base_dir>/<produto>/<vintage_id>/` - mas deliberadamente NAO uma
abstracao para "qualquer indice do mundo": este modulo so cobre o que os
produtos do projeto precisam (escrever um bundle de DataFrames + metadados
uma vez, nunca sobrescrever, listar/carregar depois). A logica ECONOMICA de
cada produto (quais colunas comparam para decidir `revised`, quais campos
entram no manifest) fica FORA deste modulo - aqui so: gerar ID, escrever
atomicamente, hashear, indexar, carregar, listar.
"""
from __future__ import annotations
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

import pandas as pd

_FORMATO_VINTAGE_ID = "%Y%m%dT%H%M%SZ"


def novo_vintage_id(agora_utc: Optional[pd.Timestamp] = None) -> str:
    """ID determinístico e ordenavel cronologicamente (a ordenacao lexica
    do formato `YYYYMMDDTHHMMSSZ` coincide com a ordenacao temporal), sem
    `:` nem outro caractere problematico em nome de diretorio no Windows,
    e sempre em UTC (nunca depende do timezone local da maquina que roda
    o script). `agora_utc` permite injecao explicita para testes
    deterministicos - precisa ser timezone-aware (nunca hora local
    implicita interpretada como UTC por engano).

    Colisao (duas vintages pedindo o mesmo segundo) NAO e resolvida aqui
    com um contador/sufixo - `criar_vintage()` levanta `FileExistsError`
    em vez de silenciosamente desambiguar, por decisao explicita (uma
    vintage e imutavel; uma colisao e um erro operacional a investigar,
    nunca uma escolha automatica de qual das duas "vence").
    """
    if agora_utc is None:
        agora_utc = pd.Timestamp.now(tz="UTC")
    elif agora_utc.tzinfo is None:
        raise ValueError("agora_utc precisa ser timezone-aware (UTC) - nunca hora local implicita")
    else:
        agora_utc = agora_utc.tz_convert("UTC")
    return agora_utc.strftime(_FORMATO_VINTAGE_ID)


def timestamp_de_vintage_id(vintage_id: str) -> pd.Timestamp:
    """Inverso de `novo_vintage_id()`. O `vintage_id` e a UNICA fonte de
    verdade do instante de criacao de uma vintage - usar isto em vez de
    uma segunda chamada a `pd.Timestamp.now()` no momento de montar o
    manifest evita duas leituras de relogio ligeiramente diferentes para
    o mesmo evento."""
    return pd.to_datetime(vintage_id, format=_FORMATO_VINTAGE_ID, utc=True)


def _sha256_arquivo(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(65536), b""):
            h.update(bloco)
    return h.hexdigest()


def _dir_produto(base_dir, produto: str) -> Path:
    return Path(base_dir) / produto


def _dir_vintage(base_dir, produto: str, vintage_id: str) -> Path:
    return _dir_produto(base_dir, produto) / vintage_id


def _caminho_index(base_dir, produto: str) -> Path:
    return _dir_produto(base_dir, produto) / "index.csv"


def criar_vintage(base_dir, produto: str, vintage_id: str,
                   arquivos: dict[str, pd.DataFrame], manifest_extra: dict,
                   index_extra: dict) -> dict:
    """Escreve UMA vintage imutavel para `produto`. `arquivos[chave]` vira
    `<chave>.csv` dentro do diretorio da vintage; o hash SHA256 de cada
    arquivo entra em `manifest["hashes"][chave]`; `manifest_extra` (campos
    especificos do produto - ver `indices_setoriais.py` para o caso
    IPIA-HRC V2) e mesclado com os campos automaticos deste modulo
    (`vintage_id`, `files`, `hashes`) e gravado como `manifest.json`.

    Atomico: tudo e escrito primeiro num diretorio temporario dentro do
    proprio `<base_dir>/<produto>/` (mesmo filesystem que o destino final,
    condicao necessaria para `os.rename` ser atomico) e so DEPOIS
    renomeado para o `vintage_id` final - uma falha a qualquer momento
    antes do rename nunca deixa uma vintage parcial visivel (o diretorio
    temporario e removido no `except`). So depois do rename bem-sucedido o
    `index.csv` e atualizado - uma vintage so entra no catalogo depois de
    existir por completo no disco (ver `_apendar_index`).

    Levanta `FileExistsError` se `vintage_id` ja existir para este
    `produto` - NUNCA sobrescreve. Em single-process local (escopo desta
    stage - sem locking distribuido), a checagem antes de comecar mais a
    checagem imediatamente antes do rename cobrem a janela de corrida
    pratica; no Windows, o proprio `os.rename` tambem levanta erro se o
    destino ja existir (garantia nativa adicional, nao a unica linha de
    defesa).

    `index_extra` deve conter o MESMO conjunto de chaves em toda chamada
    para o mesmo `produto` (vira colunas fixas do `index.csv`) -
    responsabilidade do chamador, este modulo nao conhece os campos
    especificos de nenhum produto.
    """
    destino = _dir_vintage(base_dir, produto, vintage_id)
    if destino.exists():
        raise FileExistsError(f"vintage {vintage_id!r} ja existe para {produto!r} em {destino} - "
                              f"vintages sao imutaveis, nunca sobrescritas")

    dir_produto = _dir_produto(base_dir, produto)
    dir_produto.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(tempfile.mkdtemp(prefix=f".tmp-{vintage_id}-", dir=dir_produto))
    try:
        hashes: dict[str, str] = {}
        arquivos_nomes: dict[str, str] = {}
        for chave, df in arquivos.items():
            nome_arquivo = f"{chave}.csv"
            caminho = tmp_dir / nome_arquivo
            df.to_csv(caminho, index=False)
            hashes[chave] = _sha256_arquivo(caminho)
            arquivos_nomes[chave] = nome_arquivo

        manifest = dict(manifest_extra)
        manifest["vintage_id"] = vintage_id
        manifest["files"] = arquivos_nomes
        manifest["hashes"] = hashes
        (tmp_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

        if destino.exists():  # checagem final imediatamente antes do rename
            raise FileExistsError(f"vintage {vintage_id!r} ja existe para {produto!r} - nao sobrescrita")
        os.rename(tmp_dir, destino)
    except BaseException:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise

    linha_index = {"vintage_id": vintage_id, "path": str(destino.relative_to(Path(base_dir))), **index_extra}
    _apendar_index(base_dir, produto, linha_index)
    return manifest


def _apendar_index(base_dir, produto: str, linha: dict) -> None:
    """Append-only: nunca remove/altera linhas existentes, so adiciona.
    Implementado como leitura+concat+escrita (nao um `open(..., "a")`
    linha-a-linha) porque o index.csv de uma vintage e um artefato pequeno
    (uma linha por vintage, nao um dado volumoso) - a leitura completa e
    barata e evita ter que gerenciar cabecalho/schema manualmente num
    append bruto. A escrita final passa por um arquivo `.tmp` +
    `os.replace` (atomico no mesmo diretorio) para nunca deixar o
    index.csv visivel pela metade.

    Leitura sempre com `dtype=str`: `index_extra` e um dict arbitrario do
    chamador (este modulo nao conhece o schema de nenhum produto) - um
    campo como `methodology_version="1.2"` PARECE numerico para o
    inferenciador de dtype do pandas e viraria `float 1.2` sem isso (uma
    futura versao `"1.10"` perderia o zero a direita em silencio).
    Preservar tudo como string evita essa classe de bug de forma generica,
    sem o modulo precisar saber qual campo e "realmente" numerico."""
    caminho = _caminho_index(base_dir, produto)
    novo = pd.DataFrame([linha])
    if caminho.exists():
        existente = pd.read_csv(caminho, dtype=str)
        combinado = pd.concat([existente, novo], ignore_index=True)
    else:
        combinado = novo
    tmp = caminho.with_suffix(".csv.tmp")
    combinado.to_csv(tmp, index=False)
    os.replace(tmp, caminho)


def listar_vintages(base_dir, produto: str) -> list[str]:
    """Vintage IDs em ordem cronologica (o formato `YYYYMMDDTHHMMSSZ`
    ordena lexicograficamente = cronologicamente). Lista vazia quando o
    produto ainda nao tem nenhuma vintage - nunca levanta erro."""
    caminho = _caminho_index(base_dir, produto)
    if not caminho.exists():
        return []
    idx = pd.read_csv(caminho, dtype=str)
    return sorted(idx["vintage_id"].tolist())


def ultima_vintage(base_dir, produto: str) -> Optional[str]:
    """A vintage mais recente, ou None quando ainda nao existe nenhuma -
    nunca levanta erro (o chamador usa None para saber que esta e a
    PRIMEIRA vintage, sem congelado_df)."""
    vintages = listar_vintages(base_dir, produto)
    return vintages[-1] if vintages else None


def carregar_vintage(base_dir, produto: str, vintage_id: str) -> dict:
    """Carrega o manifest + todos os arquivos CSV declarados nele.
    Retorna `{"manifest": {...}, <chave>: DataFrame, ...}` para cada
    `chave` de `manifest["files"]`. A coluna `reference_period`, quando
    presente (convencao de projeto - `docs/METODOLOGIA.md`), e convertida
    para datetime - nenhuma outra coluna recebe parsing especial aqui
    (este modulo nao conhece o schema economico de nenhum produto)."""
    dir_ = _dir_vintage(base_dir, produto, vintage_id)
    caminho_manifest = dir_ / "manifest.json"
    if not caminho_manifest.is_file():
        raise FileNotFoundError(f"vintage {vintage_id!r} nao encontrada para {produto!r} em {dir_}")
    manifest = json.loads(caminho_manifest.read_text(encoding="utf-8"))
    dados: dict = {"manifest": manifest}
    for chave, nome_arquivo in manifest["files"].items():
        df = pd.read_csv(dir_ / nome_arquivo)
        if "reference_period" in df.columns:
            df["reference_period"] = pd.to_datetime(df["reference_period"])
        dados[chave] = df
    return dados
