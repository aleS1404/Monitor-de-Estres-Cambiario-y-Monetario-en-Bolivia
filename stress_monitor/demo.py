"""Datos SIMULADOS (no reales) del paralelo, solo para ver las pantallas sin historial P2P.
Todo lo que sale de aquí debe mostrarse con la etiqueta 'DEMO'."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import data


def synthetic_gap(m: pd.DataFrame, d: pd.DataFrame | None = None, start: str = "2025-01-01",
                  end: str | None = None, seed: int = 11) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    of = data.official_daily(m, d)
    idx = pd.date_range(start, end or of.index.max(), freq="D")
    of = of.reindex(idx).ffill()
    # media de la brecha por régimen (ilustrativa) y reversión AR(1) diaria
    mean = np.where(idx < data.FECHA_REFERENCIAL, 40.0, np.where(idx < data.FECHA_FLEXIBLE, 20.0, 1.5))
    g = np.zeros(len(idx)); g[0] = mean[0]
    for t in range(1, len(idx)):
        g[t] = mean[t] + 0.93 * (g[t - 1] - mean[t - 1]) + rng.normal(0, 0.8 if idx[t] < data.FECHA_FLEXIBLE else 0.35)
    par = of.to_numpy() * (1 + g / 100)
    df = pd.DataFrame({"paralelo": par, "oficial": of.to_numpy(), "brecha_pct": g}, index=idx)
    df.attrs["demo"] = True
    return df
