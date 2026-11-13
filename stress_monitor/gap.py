"""Cap. 5 (AR(1), vida media) y análisis de la brecha oficial-paralelo (H1, H3, H5)."""
from __future__ import annotations

import warnings
import inspect

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.ar_model import AutoReg
from statsmodels.tsa.stattools import grangercausalitytests

from .stationarity import adf

MIN_OBS = 30


def daily_returns(series: pd.Series) -> pd.Series:
    """Retornos logarítmicos; un hueco de calendario no es un retorno diario."""
    s = series.dropna().sort_index()
    ret = np.log(s).diff()
    if isinstance(s.index, pd.DatetimeIndex):
        ret[s.index.to_series().diff().dt.days.ne(1)] = np.nan
    return ret.dropna()


def ar1_gap(gap: pd.Series) -> dict:
    """Ajusta gap_t = c + φ gap_{t-1} + ε. Vida media = ln(0,5)/ln(φ) (en unidades de la serie)."""
    g = gap.dropna()
    if isinstance(g.index, pd.DatetimeIndex) and (g.index.to_series().diff().dt.days.dropna() > 1).any():
        return {"ok": False, "n": len(g), "motivo": "la serie tiene huecos; AR(1) diario requiere fechas consecutivas"}
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
    """H5: correlación cruzada y Granger en días hábiles del régimen flexible."""
    levels = pd.concat([paralelo.rename("par"), oficial.rename("of")], axis=1).dropna().sort_index()
    levels = levels[levels.index >= "2026-07-01"]  # excluye el salto inicial del nuevo régimen
    if isinstance(levels.index, pd.DatetimeIndex):
        levels = levels[levels.index.dayofweek < 5]
    df = np.log(levels).diff()
    if isinstance(levels.index, pd.DatetimeIndex):
        df.loc[levels.index.to_series().diff().dt.days.gt(4)] = np.nan
    df = df.dropna()
    if len(df) < 3 * MIN_OBS:
        return {"ok": False, "n": len(df), "motivo": f"se necesitan ≥{3 * MIN_OBS} retornos hábiles comunes desde julio-2026 (hay {len(df)})"}
    if (df["of"].abs() > 1e-12).sum() < 20:
        return {"ok": False, "n": len(df), "motivo": "menos de 20 cambios observados del TCO"}
    cc = cross_correlation(df["par"], df["of"], max_lag)
    best = cc.loc[cc[cc.k != 0]["corr"].abs().idxmax()]
    out = {"ok": True, "n": len(df), "cambios_tco": int((df["of"].abs() > 1e-12).sum()),
           "cc": cc, "rezago_max": int(best.k), "corr_max": float(best["corr"])}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for name, cols in (("par→of", ["of", "par"]), ("of→par", ["par", "of"])):
            try:
                opts = {"verbose": False} if "verbose" in inspect.signature(grangercausalitytests).parameters else {}
                g = grangercausalitytests(df[cols], maxlag=min(max_lag, 5), **opts)
                out[f"granger_{name}"] = {int(L): float(g[L][0]["ssr_ftest"][1]) for L in g}
            except Exception as exc:  # noqa: BLE001
                out[f"granger_{name}"] = {}
                out[f"error_{name}"] = str(exc)
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
