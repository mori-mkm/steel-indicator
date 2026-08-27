"""Characterization tests for the Comex Stat access layer, now in
steel_indicator/sources/comex.py (Spec 0003, Stage E1 - moved from
indices_setoriais.py). Freezes: request payload, endpoint, response
parsing, the missing-'data'-field error, retry/error behavior of the
low-level POST helper, and the module-attribute late-binding mechanism
that selftest() and test_data_integration_current.py rely on to block
real network calls through indices_setoriais.comex_importacao_ncm.

No live network calls anywhere in this file: `_post_json`/`requests.post`
are always monkeypatched to canned responses or controlled failures.

`_post_json` is a private, single-consumer helper of the adapter and is
NOT re-exported into indices_setoriais.py (no other code there ever called
it) - so tests exercising it patch `steel_indicator.sources.comex`
directly, while tests exercising the public, re-exported
`comex_importacao_ncm` go through `indices_setoriais` (`m`), exactly as
production code (`_comex_bobina_bruto`) does.
"""
import pandas as pd
import pytest

import indices_setoriais as m
import steel_indicator.sources.comex as comex_mod


def _post_json_stub(respostas):
    """Substitui comex_mod._post_json por um stub que devolve `respostas`
    (um dict fixo) e registra as chamadas (url, payload) em `chamadas`."""
    chamadas = []

    def _stub(url, payload, tentativas=3):
        chamadas.append((url, payload))
        return respostas

    return _stub, chamadas


def test_comex_importacao_ncm_monta_payload_e_usa_endpoint_esperados():
    stub, chamadas = _post_json_stub({"data": {"list": []}})
    original = comex_mod._post_json
    comex_mod._post_json = stub
    try:
        m.comex_importacao_ncm(["72083610", "72082500"], 2020, 2021)
    finally:
        comex_mod._post_json = original

    assert len(chamadas) == 1
    url, payload = chamadas[0]
    assert url == m.COMEX_URL
    assert payload == {
        "flow": "import",
        "monthDetail": True,
        "period": {"from": "2020-01", "to": "2021-12"},
        "filters": [{"filter": "ncm", "values": ["72083610", "72082500"]}],
        "details": ["ncm", "country"],
        "metrics": ["metricFOB", "metricKG", "metricFreight", "metricInsurance"],
    }


def test_comex_importacao_ncm_retorna_dataframe_da_lista_devolvida():
    linhas = [
        {"ncm": "72083610", "country": "China", "year": 2020, "monthNumber": 1,
         "metricFOB": 100.0, "metricKG": 10.0, "metricFreight": 5.0, "metricInsurance": 1.0},
        {"ncm": "72083610", "country": "Coreia do Sul", "year": 2020, "monthNumber": 1,
         "metricFOB": 200.0, "metricKG": 20.0, "metricFreight": 8.0, "metricInsurance": 2.0},
    ]
    stub, _ = _post_json_stub({"data": {"list": linhas}})
    original = comex_mod._post_json
    comex_mod._post_json = stub
    try:
        df = m.comex_importacao_ncm(["72083610"], 2020, 2020)
    finally:
        comex_mod._post_json = original

    pd.testing.assert_frame_equal(df, pd.DataFrame(linhas))


def test_comex_importacao_ncm_lista_vazia_retorna_dataframe_vazio_sem_erro():
    stub, _ = _post_json_stub({"data": {"list": []}})
    original = comex_mod._post_json
    comex_mod._post_json = stub
    try:
        df = m.comex_importacao_ncm(["72083610"], 2020, 2020)
    finally:
        comex_mod._post_json = original

    assert df.empty


def test_comex_importacao_ncm_resposta_sem_campo_data_levanta_value_error():
    stub, _ = _post_json_stub({"foo": "bar"})
    original = comex_mod._post_json
    comex_mod._post_json = stub
    try:
        with pytest.raises(ValueError, match="foo"):
            m.comex_importacao_ncm(["72083610"], 2020, 2020)
    finally:
        comex_mod._post_json = original


def test_post_json_esgota_tentativas_e_relanca_erro_sem_dormir_de_verdade():
    chamadas_post = {"n": 0}

    def _post_sempre_falha(*args, **kwargs):
        chamadas_post["n"] += 1
        raise ConnectionError("falha simulada de rede")

    import requests
    original_post = requests.post
    original_sleep = comex_mod.time.sleep
    requests.post = _post_sempre_falha
    comex_mod.time.sleep = lambda segundos: None  # evita esperar de verdade no teste
    try:
        with pytest.raises(ConnectionError):
            comex_mod._post_json(m.COMEX_URL, {"flow": "import"}, tentativas=3)
    finally:
        requests.post = original_post
        comex_mod.time.sleep = original_sleep

    assert chamadas_post["n"] == 3


def test_comex_importacao_ncm_pode_ser_substituido_via_atributo_do_modulo():
    """Trava de seguranca especifica para a extracao (Stage E1): selftest()
    e test_data_integration_current.py bloqueiam rede real reatribuindo
    `m.comex_importacao_ncm` a um stub, confiando que `_comex_bobina_bruto`
    resolve o nome no NAMESPACE do modulo (late binding), nao numa
    referencia direta capturada em import. Depois que `comex_importacao_ncm`
    for importado de steel_indicator.sources.comex, esse mecanismo so
    continua funcionando se `_comex_bobina_bruto` permanecer em
    indices_setoriais.py chamando o nome pelo proprio namespace do modulo."""
    chamadas = []

    def _stub(ncm, ano_ini, ano_fim):
        chamadas.append((tuple(ncm), ano_ini, ano_fim))
        return pd.DataFrame({"marcador": ["veio-do-stub"]})

    original = m.comex_importacao_ncm
    m.comex_importacao_ncm = _stub
    try:
        df = m._comex_bobina_bruto(2020, 2021)
    finally:
        m.comex_importacao_ncm = original

    assert len(chamadas) == 1
    ncm_chamado, ano_ini, ano_fim = chamadas[0]
    assert ano_ini == 2020 and ano_fim == 2021
    assert set(ncm_chamado) == set(sum(m.NCM_BOBINA_QUENTE.values(), []))
    assert df["marcador"].iloc[0] == "veio-do-stub"
