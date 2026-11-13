"""Cap. 5 (AR(1), vida media) y análisis de la brecha oficial-paralelo (H1, H3, H5)."""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.ar_model import AutoReg
from statsmodels.tsa.stattools import grangercausalitytests

from .stationarity import adf

MIN_OBS = 30


def ar1_gap(gap: pd.Series) -> dict:
    """Ajusta gap_t = c + φ gap_{t-1} + ε. Vida media = ln(0,5)/ln(φ) (en unidades de la serie)."""
    g = gap.dropna()
    if len(g) < MIN_OBS:
        return {"ok": False, "n": len(g), "motivo": f"se necesitan ≥{MIN_OBS} observaciones (hay {len(g)})"}
    res = AutoReg(g.to_numpy(), lags=1, trend="c").fit()
    c, phi = res.params
    sigma = float(np.sqrt(res.sigma2))
    half = float(np.log(0.5) / np.log(phi)) if 0 < phi < 1 else float("inf")
    mu = float(c / (1 - phi)) if abs(phi) < 1 else float("nan")
    sd_est = float(sigma / np.sqrt(1 - phi ** 2)) if abs(phi) < 1 else float("nan")
    return {"ok": True, "n": len(g), "phi": float(phi), "c": float(c), "sigma": sigma,
            "vida_media": half, "media_larga": mu, "banda95": (mu - 1.96 * sd_est, mu + 1.96 * sd_est),
            "adf": adf(g), "se_phi": float(res.bse[1])}


def cross_correlation(x: pd.Series, y: pd.Series, max_lag: int = 10) -> pd.DataFrame:
    """corr(x_t, y_{t+k}). k>0 ⇒ x se adelanta a y."""
    df = pd.concat([x.rename("x"), y.rename("y")], axis=1).dropna()
    rows = []
    for k in range(-max_lag, max_lag + 1):
        rows.append({"k": k, "corr": df["x"].corr(df["y"].shift(-k))})
    out = pd.DataFrame(rows)
    out.attrs["banda95"] = 1.96 / np.sqrt(len(df)) if len(df) else np.nan
    return out


def lead_lag(paralelo: pd.Series, oficial: pd.Series, max_lag: int = 7) -> dict:
    """H5: ¿el paralelo se adelanta al oficial? Correlación cruzada de retornos + Granger."""
    r_par = np.log(paralelo).diff().dropna()
    r_of = np.log(oficial).diff().dropna()
    df = pd.concat([r_par.rename("par"), r_of.rename("of")], axis=1).dropna()
    if len(df) < 3 * MIN_OBS:
        return {"ok": False, "n": len(df), "motivo": f"se necesitan ≥{3 * MIN_OBS} retornos diarios comunes (hay {len(df)})"}
    cc = cross_correlation(df["par"], df["of"], max_lag)
    best = cc.loc[cc[cc.k != 0]["corr"].abs().idxmax()]
    out = {"ok": True, "n": len(df), "cc": cc, "rezago_max": int(best.k), "corr_max": float(best["corr"])}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for name, cols in (("par→of", ["of", "par"]), ("of→par", ["par", "of"])):
            try:
                g = grangercausalitytests(df[cols], maxlag=min(max_lag, 5), verbose=False)
                out[f"granger_{name}"] = {L: float(g[L][0]["ssr_ftest"][1]) for L in g}
            except Exception:  # noqa: BLE001
                out[f"granger_{name}"] = {}
    return out


def volatility_by_regime(ret: pd.Series, split: str) -> dict:
    """H3: compara desviación estándar de retornos antes/después de `split` (Levene, robusto a no normalidad)."""
    a, b = ret[ret.index < split].dropna(), ret[ret.index >= split].dropna()
    if len(a) < 10 or len(b) < 10:
        return {"ok": False, "n_antes": len(a), "n_despues": len(b), "motivo": "muestras insuficientes (<10)"}
    stat, p = stats.levene(a, b, center="median")
    return {"ok": True, "n_antes": len(a), "n_despues": len(b), "sd_antes": float(a.std()),
            "sd_despues": float(b.std()), "razon": float(b.std() / a.std()), "levene_p": float(p)}


def monthly_gap(gap_daily: pd.DataFrame) -> pd.Series:
    if gap_daily.empty:
        return pd.Series(dtype=float)
    s = gap_daily["brecha_pct"].resample("ME").mean()
    s.index = s.index.normalize()
    return s
