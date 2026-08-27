"""Unit tests for steel_indicator.storage.vintage_store - persistencia
append-only/imutavel/local de vintages de publicacao (Stage G2, ADR 0012).
Deterministic, no network, sempre em tmp_path (nunca escreve em
data/processed real).

Prova: vintage_id determinístico/ordenavel/UTC; primeira vintage criada
corretamente; colisao de vintage_id levanta erro sem sobrescrever; hash
SHA256 bate com o arquivo real; carregar/listar/ultima funcionam; vintage
anterior permanece intacta apos criar uma nova; falha durante a escrita
nao registra vintage invalida no index.
"""
import hashlib

import pandas as pd
import pytest

from steel_indicator.storage import vintage_store as vs


# --- novo_vintage_id / timestamp_de_vintage_id ------------------------------

def test_novo_vintage_id_formato_ordenavel_sem_caracteres_problematicos():
    vid = vs.novo_vintage_id(pd.Timestamp("2026-08-27 14:30:12", tz="UTC"))
    assert vid == "20260827T143012Z"
    assert ":" not in vid and "/" not in vid and "\\" not in vid


def test_novo_vintage_id_ordena_cronologicamente():
    v1 = vs.novo_vintage_id(pd.Timestamp("2026-01-01 00:00:00", tz="UTC"))
    v2 = vs.novo_vintage_id(pd.Timestamp("2026-06-15 10:00:00", tz="UTC"))
    assert sorted([v2, v1]) == [v1, v2]


def test_novo_vintage_id_independe_de_timezone_local():
    # mesmo instante, informado em fusos diferentes -> mesmo vintage_id UTC.
    v_utc = vs.novo_vintage_id(pd.Timestamp("2026-08-27 14:30:12", tz="UTC"))
    v_sp = vs.novo_vintage_id(pd.Timestamp("2026-08-27 11:30:12", tz="America/Sao_Paulo"))
    assert v_utc == v_sp


def test_novo_vintage_id_rejeita_timestamp_sem_timezone():
    with pytest.raises(ValueError, match="timezone-aware"):
        vs.novo_vintage_id(pd.Timestamp("2026-08-27 14:30:12"))


def test_timestamp_de_vintage_id_e_inverso_de_novo_vintage_id():
    original = pd.Timestamp("2026-08-27 14:30:12", tz="UTC")
    vid = vs.novo_vintage_id(original)
    assert vs.timestamp_de_vintage_id(vid) == original


# --- criar_vintage / carregar_vintage ---------------------------------------

def _arquivos_exemplo():
    return {
        "official": pd.DataFrame({"reference_period": [pd.Timestamp("2024-01-01")], "valor": [1.0]}),
        "provisional": pd.DataFrame({"reference_period": [pd.Timestamp("2024-02-01")], "valor": [2.0]}),
    }


def test_primeira_vintage_e_criada_corretamente(tmp_path):
    manifest = vs.criar_vintage(tmp_path, "produto_teste", "20260827T143012Z",
                                arquivos=_arquivos_exemplo(),
                                manifest_extra={"algo": "valor"}, index_extra={"campo_x": 42})
    assert manifest["vintage_id"] == "20260827T143012Z"
    assert manifest["algo"] == "valor"
    assert set(manifest["files"]) == {"official", "provisional"}
    assert (tmp_path / "produto_teste" / "20260827T143012Z" / "manifest.json").is_file()
    assert (tmp_path / "produto_teste" / "20260827T143012Z" / "official.csv").is_file()
    assert (tmp_path / "produto_teste" / "20260827T143012Z" / "provisional.csv").is_file()
    assert (tmp_path / "produto_teste" / "index.csv").is_file()


def test_hash_sha256_bate_com_arquivo_real(tmp_path):
    manifest = vs.criar_vintage(tmp_path, "produto_teste", "20260827T143012Z",
                                arquivos=_arquivos_exemplo(), manifest_extra={}, index_extra={})
    caminho = tmp_path / "produto_teste" / "20260827T143012Z" / "official.csv"
    hash_real = hashlib.sha256(caminho.read_bytes()).hexdigest()
    assert manifest["hashes"]["official"] == hash_real


def test_carregar_vintage_devolve_manifest_e_dataframes(tmp_path):
    vs.criar_vintage(tmp_path, "produto_teste", "20260827T143012Z",
                     arquivos=_arquivos_exemplo(), manifest_extra={"x": 1}, index_extra={})
    carregado = vs.carregar_vintage(tmp_path, "produto_teste", "20260827T143012Z")
    assert carregado["manifest"]["x"] == 1
    assert carregado["official"]["valor"].iloc[0] == 1.0
    assert carregado["official"]["reference_period"].iloc[0] == pd.Timestamp("2024-01-01")
    assert pd.api.types.is_datetime64_any_dtype(carregado["official"]["reference_period"])


def test_carregar_vintage_inexistente_levanta_erro_explicito(tmp_path):
    with pytest.raises(FileNotFoundError):
        vs.carregar_vintage(tmp_path, "produto_teste", "20990101T000000Z")


# --- imutabilidade / colisao -------------------------------------------------

def test_tentativa_de_sobrescrever_vintage_id_existente_falha(tmp_path):
    vs.criar_vintage(tmp_path, "produto_teste", "20260827T143012Z",
                     arquivos=_arquivos_exemplo(), manifest_extra={}, index_extra={})
    with pytest.raises(FileExistsError):
        vs.criar_vintage(tmp_path, "produto_teste", "20260827T143012Z",
                         arquivos={"official": pd.DataFrame({"reference_period": [], "valor": []})},
                         manifest_extra={}, index_extra={})
    # a vintage original permanece intacta - nao foi sobrescrita.
    carregado = vs.carregar_vintage(tmp_path, "produto_teste", "20260827T143012Z")
    assert carregado["official"]["valor"].iloc[0] == 1.0


def test_vintage_anterior_permanece_intacta_apos_criar_nova(tmp_path):
    vs.criar_vintage(tmp_path, "produto_teste", "20260101T000000Z",
                     arquivos=_arquivos_exemplo(), manifest_extra={"v": "A"}, index_extra={})
    antes = (tmp_path / "produto_teste" / "20260101T000000Z" / "official.csv").read_bytes()

    vs.criar_vintage(tmp_path, "produto_teste", "20260201T000000Z",
                     arquivos={"official": pd.DataFrame({"reference_period": [pd.Timestamp("2024-03-01")],
                                                          "valor": [999.0]})},
                     manifest_extra={"v": "B"}, index_extra={})

    depois = (tmp_path / "produto_teste" / "20260101T000000Z" / "official.csv").read_bytes()
    assert antes == depois  # byte-for-byte intacta
    carregado = vs.carregar_vintage(tmp_path, "produto_teste", "20260101T000000Z")
    assert carregado["manifest"]["v"] == "A"


def test_falha_durante_escrita_nao_registra_vintage_invalida_no_index(tmp_path, monkeypatch):
    class DataFrameQuebrado(pd.DataFrame):
        def to_csv(self, *a, **kw):
            raise RuntimeError("falha simulada de escrita")

    arquivos_quebrados = {"official": DataFrameQuebrado({"reference_period": [pd.Timestamp("2024-01-01")]})}
    with pytest.raises(RuntimeError, match="falha simulada"):
        vs.criar_vintage(tmp_path, "produto_teste", "20260827T143012Z",
                         arquivos=arquivos_quebrados, manifest_extra={}, index_extra={})

    assert vs.listar_vintages(tmp_path, "produto_teste") == []
    assert vs.ultima_vintage(tmp_path, "produto_teste") is None
    # nenhum diretorio de vintage (nem temporario) deve sobrar visivel.
    dir_produto = tmp_path / "produto_teste"
    if dir_produto.exists():
        assert list(dir_produto.iterdir()) == []


def test_falha_no_catalogo_apos_rename_bem_sucedido_nao_cria_linha_invalida(tmp_path, monkeypatch):
    # cenario DIFERENTE do teste acima: aqui o rename (finalizacao da
    # vintage) JA teve sucesso quando a falha acontece (_apendar_index
    # falha) - o diretorio da vintage existe, completo e imutavel, no
    # disco, mas NUNCA aparece no catalogo. Prova a garantia especifica
    # "nenhuma linha invalida no index.csv" mesmo quando a falha e DEPOIS
    # do ponto em que a vintage ja e valida - nao so antes dele.
    def _apendar_quebrado(*a, **kw):
        raise RuntimeError("falha simulada ao atualizar o index.csv")

    monkeypatch.setattr(vs, "_apendar_index", _apendar_quebrado)
    with pytest.raises(RuntimeError, match="falha simulada ao atualizar"):
        vs.criar_vintage(tmp_path, "produto_teste", "20260827T143012Z",
                         arquivos=_arquivos_exemplo(), manifest_extra={}, index_extra={})

    # o index.csv nunca chegou a existir - nenhuma linha invalida.
    assert vs.listar_vintages(tmp_path, "produto_teste") == []
    assert vs.ultima_vintage(tmp_path, "produto_teste") is None
    # mas a vintage em si esta la, completa e carregavel por ID direto -
    # "orfa" do catalogo, nunca corrompida ou parcial.
    carregado = vs.carregar_vintage(tmp_path, "produto_teste", "20260827T143012Z")
    assert carregado["official"]["valor"].iloc[0] == 1.0


# --- listar_vintages / ultima_vintage ---------------------------------------

def test_listar_vintages_retorna_ordem_cronologica(tmp_path):
    for vid in ("20260301T000000Z", "20260101T000000Z", "20260201T000000Z"):
        vs.criar_vintage(tmp_path, "produto_teste", vid,
                         arquivos={"official": pd.DataFrame({"reference_period": [], "valor": []})},
                         manifest_extra={}, index_extra={})
    assert vs.listar_vintages(tmp_path, "produto_teste") == [
        "20260101T000000Z", "20260201T000000Z", "20260301T000000Z"]


def test_ultima_vintage_funciona_e_devolve_none_quando_vazio(tmp_path):
    assert vs.ultima_vintage(tmp_path, "produto_teste") is None
    vs.criar_vintage(tmp_path, "produto_teste", "20260101T000000Z",
                     arquivos={"official": pd.DataFrame({"reference_period": [], "valor": []})},
                     manifest_extra={}, index_extra={})
    vs.criar_vintage(tmp_path, "produto_teste", "20260201T000000Z",
                     arquivos={"official": pd.DataFrame({"reference_period": [], "valor": []})},
                     manifest_extra={}, index_extra={})
    assert vs.ultima_vintage(tmp_path, "produto_teste") == "20260201T000000Z"


def test_index_preserva_campos_texto_que_parecem_numericos_entre_appends(tmp_path):
    # index_extra e um dict arbitrario do chamador - um campo como
    # "methodology_version"="1.2" PARECE numerico ao inferenciador de
    # dtype do pandas; sem dtype=str na leitura, a 2a vintage corromperia
    # o valor da 1a ao reler+concatenar+reescrever o index.csv inteiro
    # (uma futura versao "1.10" perderia o zero a direita em silencio).
    vs.criar_vintage(tmp_path, "produto_teste", "20260101T000000Z",
                     arquivos={"official": pd.DataFrame({"reference_period": [], "valor": []})},
                     manifest_extra={}, index_extra={"methodology_version": "1.2"})
    vs.criar_vintage(tmp_path, "produto_teste", "20260201T000000Z",
                     arquivos={"official": pd.DataFrame({"reference_period": [], "valor": []})},
                     manifest_extra={}, index_extra={"methodology_version": "1.10"})
    idx = pd.read_csv(tmp_path / "produto_teste" / "index.csv", dtype=str)
    assert list(idx["methodology_version"]) == ["1.2", "1.10"]


def test_index_e_append_only_mantem_linhas_anteriores(tmp_path):
    vs.criar_vintage(tmp_path, "produto_teste", "20260101T000000Z",
                     arquivos={"official": pd.DataFrame({"reference_period": [], "valor": []})},
                     manifest_extra={}, index_extra={"campo": "primeiro"})
    vs.criar_vintage(tmp_path, "produto_teste", "20260201T000000Z",
                     arquivos={"official": pd.DataFrame({"reference_period": [], "valor": []})},
                     manifest_extra={}, index_extra={"campo": "segundo"})
    idx = pd.read_csv(tmp_path / "produto_teste" / "index.csv")
    assert list(idx["campo"]) == ["primeiro", "segundo"]
