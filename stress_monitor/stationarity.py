"""Cap. 1-2 (procesos estocásticos, estacionariedad) y cap. 5 (densidad espectral)."""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from scipy import signal
from statsmodels.tsa.stattools import acf, adfuller, pacf


def adf(x: pd.Series, regression: str = "c") -> dict:
    x = pd.Series(x).dropna()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        stat, p, lags, nobs, crit, _ = adfuller(x, regression=regression, autolag="AIC")
    return {"estadistico": stat, "p_valor": p, "rezagos": lags, "n": nobs,
            "critico_5%": crit["5%"], "estacionaria_5%": bool(p < 0.05)}


def adf_table(df: pd.DataFrame, cols: list[str], start: str | None = "1995-01-01") -> pd.DataFrame:
    """ADF sobre nivel, log, diferencia y log-diferencia (x100)."""
    rows = []
    for c in cols:
        s = df[c].dropna()
        if start:
            s = s[s.index >= start]
        variants = {"nivel": s}
        if (s > 0).all():
            variants["log"] = np.log(s)
            variants["Δlog ×100"] = np.log(s).diff().dropna() * 100
        variants["Δ"] = s.diff().dropna()
        for name, v in variants.items():
            r = adf(v)
            rows.append({"variable": c, "transformación": name, **r})
    out = pd.DataFrame(rows)
    return out


def sample_moments(x: pd.Series, nlags: int = 12) -> dict:
    x = pd.Series(x).dropna()
    gam = acf(x, nlags=nlags, adjusted=False, fft=True) * x.var(ddof=0)
    return {"media": x.mean(), "varianza": x.var(ddof=0), "autocovarianzas": gam.tolist()}


def acf_pacf(x: pd.Series, nlags: int = 24) -> pd.DataFrame:
    x = pd.Series(x).dropna()
    n = len(x)
    nlags = min(nlags, n // 2 - 1)
    a = acf(x, nlags=nlags, fft=True)
    p = pacf(x, nlags=nlags, method="ywm")
    return pd.DataFrame({"lag": range(nlags + 1), "acf": a, "pacf": p, "banda95": 1.96 / np.sqrt(n)})


def periodogram(x: pd.Series, fs: float = 1.0, top: int = 3, min_freq: float = 0.0) -> dict:
    """Densidad espectral estimada por periodograma. fs=1 → frecuencias en ciclos/mes."""
    x = pd.Series(x).dropna().to_numpy(dtype=float)
    f, pxx = signal.periodogram(x, fs=fs, detrend="constant", window="hann", scaling="density")
    f, pxx = f[1:], pxx[1:]  # sin frecuencia 0
    keep = f >= min_freq    # p. ej. min_freq=1/60 ignora periodos >60 meses (indistinguibles de la tendencia)
    f, pxx = f[keep], pxx[keep]
    order = np.argsort(pxx)[::-1]
    picks, used = [], []
    for i in order:
        if all(abs(f[i] - u) > 1.5 / len(x) for u in used):
            picks.append({"periodo_meses": float(1 / f[i]), "frecuencia": float(f[i]), "potencia": float(pxx[i])})
            used.append(f[i])
        if len(picks) == top:
            break
    return {"f": f, "pxx": pxx, "picos": picks}
