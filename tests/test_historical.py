"""Regresiones de procedencia, alineación y uso de los historiales diarios."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bcb_pipeline.historical import parse_official, parse_parallel
from stress_monitor import data, gap


def test_parsers_rechazan_fechas_duplicadas_y_valores_invalidos():
    dates = pd.date_range("2026-01-01", periods=100, freq="D")
    good = pd.DataFrame({"date": dates, "median_bob_per_usd": 12.0}).to_csv(index=False).encode()
    assert len(parse_parallel(b"# historico\n" + good)) == 100
    bad = good.replace(b"2026-01-02", b"2026-01-01")
    with pytest.raises(ValueError, match="duplicadas"):
        parse_parallel(bad)
    official = pd.DataFrame({"Fecha": dates, "Valor": 12.0}).to_csv(index=False, sep=";").encode()
    assert len(parse_official(official)) == 100
    with pytest.raises(ValueError, match="fuera de rango"):
        parse_official(official.replace(b"12.0", b"100.0", 1))


def test_tco_excluye_compra_fija_previa_y_brecha_no_mezcla_fuentes(tmp_path):
    official_file = tmp_path / "bcb.csv"
    official_file.write_text("Fecha;Valor\n2026-06-28;6.86\n2026-06-29;9.70\n2026-06-30;9.80\n", encoding="utf-8")
    tco = data.load_bcb_tco(official_file)
    assert list(tco.index.strftime("%Y-%m-%d")) == ["2026-06-29", "2026-06-30"]
    ext = pd.DataFrame({"paralelo": [11.0, 11.1]}, index=tco.index)
    own = pd.DataFrame({"p2p_venta": [30.0, 30.0]}, index=tco.index)
    m = pd.DataFrame({"tc_oficial": [9.0], "tc_fijo_bolsin": [6.96]}, index=pd.DatetimeIndex(["2026-06-28"]))
    g = data.build_gap(m, None, own, pd.DataFrame(), external=ext, official_tco=tco)
    assert g["paralelo"].tolist() == [11.0, 11.1]
    assert g["oficial"].tolist() == [9.7, 9.8]
    assert g["fuente_p2p"].eq("paralelo.bo (mediana P2P)").all()


def test_retornos_diarios_y_ar1_no_cruzan_huecos():
    idx = pd.DatetimeIndex(["2024-11-01", "2024-11-02", "2026-07-01", "2026-07-02"])
    s = pd.Series([10.0, 10.1, 12.0, 12.1], index=idx)
    assert len(gap.daily_returns(s)) == 2
    assert not gap.ar1_gap(s)["ok"]


def test_lead_lag_detecta_adelanto_con_datos_diarios():
    rng = np.random.default_rng(2026)
    idx = pd.bdate_range("2026-07-01", periods=120)
    pr = rng.normal(0, .01, len(idx))
    of = np.r_[0.0, pr[:-1]] + rng.normal(0, .001, len(idx))
    paralelo = pd.Series(12.0 * np.exp(pr.cumsum()), index=idx)
    oficial = pd.Series(12.0 * np.exp(of.cumsum()), index=idx)
    result = gap.lead_lag(paralelo, oficial)
    assert result["ok"] and result["rezago_max"] == 1
    assert result["granger_par→of"][1] < .05
