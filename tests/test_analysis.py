"""Pruebas con casos de respuesta conocida (simulaciones con parámetros verdaderos)."""
import numpy as np
import pandas as pd
import pytest

from stress_monitor import data, gap, markov as mk, simulation as sim, stationarity as stt

RNG = np.random.default_rng(0)


def simulate_chain(P, n, seed=1):
    rng = np.random.default_rng(seed)
    x = [0]
    for _ in range(n - 1):
        x.append(rng.choice(len(P), p=P[x[-1]]))
    return pd.Series(x, index=pd.date_range("1990-01-31", periods=n, freq="ME"))


P_TRUE = np.array([[.90, .08, .02], [.20, .60, .20], [.05, .25, .70]])


def test_markov_recupera_matriz_verdadera():
    s = simulate_chain(P_TRUE, 20_000)
    fit = mk.fit_markov(s)
    assert np.allclose(fit.P, P_TRUE, atol=0.03)
    assert np.allclose(fit.stationary @ P_TRUE, fit.stationary, atol=0.02)
    assert np.allclose(fit.sojourn, 1 / (1 - P_TRUE.diagonal()), rtol=0.1)


def test_estacionaria_exacta():
    pi = mk.stationary_distribution(P_TRUE)
    assert np.isclose(pi.sum(), 1) and np.allclose(pi @ P_TRUE, pi)


def test_probabilidades_futuras_suman_uno():
    pr = mk.forecast_state_probs(P_TRUE, 2, (1, 3, 6, 60))
    assert all(np.isclose(p.sum(), 1) for p in pr.values())
    assert np.allclose(pr[60], mk.stationary_distribution(P_TRUE), atol=1e-3)


def test_independencia_detecta_dependencia_y_no_en_iid():
    dep = mk.test_independence(mk.fit_markov(simulate_chain(P_TRUE, 3000)).counts)
    assert dep["p_valor"] < 1e-6
    iid = pd.Series(np.random.default_rng(3).integers(0, 3, 3000))
    assert mk.test_independence(mk.fit_markov(iid).counts)["p_valor"] > 0.01


def test_orden2_no_rechaza_cadena_de_orden1():
    s = simulate_chain(P_TRUE, 6000, seed=5)
    assert mk.test_second_order(s)["p_valor"] > 0.01


def test_ar1_recupera_phi_y_vida_media():
    phi, n = 0.9, 4000
    e = np.random.default_rng(2).normal(0, 1, n)
    x = np.zeros(n)
    for t in range(1, n):
        x[t] = 2 + phi * x[t - 1] + e[t]
    r = gap.ar1_gap(pd.Series(x))
    assert abs(r["phi"] - phi) < 0.03
    assert abs(r["vida_media"] - np.log(.5) / np.log(phi)) < 1.5
    assert abs(r["media_larga"] - 2 / (1 - phi)) < 2


def test_ar1_pocas_observaciones():
    assert gap.ar1_gap(pd.Series(range(10)))["ok"] is False


def test_adf_distingue_ruido_de_paseo_aleatorio():
    ruido = pd.Series(np.random.default_rng(4).normal(size=500))
    assert stt.adf(ruido)["estacionaria_5%"]
    assert not stt.adf(ruido.cumsum())["estacionaria_5%"]


def test_periodograma_encuentra_ciclo_de_12():
    t = np.arange(480)
    x = np.sin(2 * np.pi * t / 12) + 0.3 * np.random.default_rng(1).normal(size=480)
    assert abs(stt.periodogram(pd.Series(x))["picos"][0]["periodo_meses"] - 12) < 0.5


def test_gbm_media_teorica():
    s0, mu, sg, T = 100.0, 0.01, 0.05, 12
    p = sim.gbm_paths(s0, mu, sg, T, 200_000, seed=1)
    assert np.isclose(p[:, -1].mean(), s0 * np.exp(mu * T), rtol=0.01)
    assert np.allclose(p[:, 0], s0)


def test_fx_params_recupera_sigma_con_datos_irregulares():
    sg = 0.01
    days = np.sort(np.random.default_rng(0).choice(np.arange(1, 800), 300, replace=False))
    idx = pd.Timestamp("2026-01-01") + pd.to_timedelta(days, unit="D")
    lvl = np.cumsum(np.random.default_rng(1).normal(0, sg, 800))[days - 1]
    r = sim.fx_params(pd.Series(12 * np.exp(lvl), index=idx))
    assert abs(r["sigma_diario"] - sg) < 0.002


def test_fx_cost_simulation_percentiles_ordenados():
    o = sim.fx_cost_simulation(1000, 30, 12.0, 0.0, 0.005)
    assert o["p5"] < o["p50"] < o["p95"]
    assert abs(o["p50"] - 12_000) < 300


def test_neutraliza_efecto_de_valoracion():
    """MN fija en Bs y ME fija en USD; el TC se duplica ⇒ la bolivianización a TC vigente cae
    pero el cambio NEUTRAL debe ser ~0."""
    idx = pd.date_range("2025-01-31", periods=14, freq="ME")
    tc = np.r_[np.full(7, 6.96), np.full(7, 13.92)]
    mn_bs = 200_000.0
    m = pd.DataFrame({"tc_fijo_bolsin": 6.96, "tc_oficial": np.where(tc > 7, tc, np.nan),
                      "depositos_mn": mn_bs / tc, "depositos_me": 3000.0}, index=idx)
    vig = data.bolivianizacion_tc_vigente(m)
    assert vig.iloc[-1] < vig.iloc[0] - 3          # cae por valoración
    neutral = data.bolivianizacion_neutral_change(m, 6).dropna()
    assert neutral.abs().max() < 1e-9               # sin cambio de composición real
    assert abs(data.bolivianizacion_tc_fijo(m).iloc[-1] - data.bolivianizacion_tc_fijo(m).iloc[0]) < 1e-9


def test_brecha_con_p2p_sintetico_real_flag():
    idx = pd.date_range("2026-07-01", periods=60, freq="D")
    col = pd.DataFrame({"p2p_venta": 12.2, "of_venta": 12.0}, index=idx)
    m = pd.DataFrame({"tc_oficial": [12.0], "tc_fijo_bolsin": [6.96], "tc_referencial_venta": [np.nan]},
                     index=pd.DatetimeIndex(["2026-07-31"]))
    g = data.build_gap(m, None, col, pd.DataFrame())
    assert len(g) > 0 and np.isclose(g["brecha_pct"].iloc[-1], (12.2 / 12.0 - 1) * 100)


@pytest.mark.skipif(not (data.PROCESSED / "monthly_key.csv").exists(), reason="sin datos procesados")
def test_datos_reales_indice_y_estados():
    m = data.load_monthly()
    ci = mk.stress_index(m)
    s = mk.classify(ci["indice"])
    assert s.isin([0, 1, 2]).all() and s.index.is_monotonic_increasing
    assert abs(s.value_counts(normalize=True).get(2, 0) - 0.15) < 0.03   # ~percentil 85
