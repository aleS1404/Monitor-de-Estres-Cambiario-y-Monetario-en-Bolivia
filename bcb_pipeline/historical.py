"""Descarga copias verificables de las series diarias externas usadas en la brecha.

El paralelo es la mediana P2P publicada por paralelo.bo (CC BY 4.0), no la
cotización Binance del recolector ni el promedio USDT del PDF del BCB.
"""
from __future__ import annotations

import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

PARALLEL_URL = "https://paralelo.bo/api/v1/historical.csv"
OFFICIAL_URL = "https://www.bcb.gob.bo/grafico_evolutivo/download.php?serie=tipo_de_cambio&format=csv"
DEFAULT_DIR = Path("data/external")


def parse_parallel(content: bytes) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(content), comment="#", parse_dates=["date"])
    if list(df.columns) != ["date", "median_bob_per_usd"]:
        raise ValueError("Columnas inesperadas en el historial de paralelo.bo")
    _validate(df, "date", "median_bob_per_usd")
    return df


def parse_official(content: bytes) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(content), sep=";", encoding="utf-8-sig", parse_dates=["Fecha"])
    if list(df.columns) != ["Fecha", "Valor"]:
        raise ValueError("Columnas inesperadas en el historial diario del BCB")
    _validate(df, "Fecha", "Valor")
    return df


def _validate(df: pd.DataFrame, date_col: str, value_col: str) -> None:
    if len(df) < 90 or df[date_col].isna().any() or df[date_col].duplicated().any():
        raise ValueError("Historial vacío, corto o con fechas inválidas/duplicadas")
    if not df[date_col].is_monotonic_increasing:
        raise ValueError("Las fechas del historial no están ordenadas")
    values = pd.to_numeric(df[value_col], errors="coerce")
    if values.isna().any() or not values.between(5, 30).all():
        raise ValueError("Cotizaciones inválidas o fuera de rango")


def fetch_history(out_dir: Path = DEFAULT_DIR) -> dict:
    """Guarda los CSV originales y un manifiesto con URL, fecha, hash y cobertura."""
    out_dir = Path(out_dir)
    sources = [
        ("paralelo_bo_historical.csv", PARALLEL_URL, parse_parallel, "date", "CC BY 4.0; mediana P2P, con backfill histórico"),
        ("bcb_tco_daily.csv", OFFICIAL_URL, parse_official, "Fecha", "BCB; TCO diario desde 2026-06-29"),
    ]
    downloads = []
    for name, url, parser, date_col, note in sources:
        response = requests.get(url, timeout=60, headers={"User-Agent": "monitor-estres-bolivia-academico"})
        response.raise_for_status()
        df = parser(response.content)
        downloads.append((name, response.content, {
            "url": url, "retrieved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "sha256": hashlib.sha256(response.content).hexdigest(), "rows": len(df),
            "first_date": str(df[date_col].min().date()), "last_date": str(df[date_col].max().date()),
            "note": note,
        }))
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, content, _ in downloads:
        (out_dir / name).write_bytes(content)
    manifest = {name: info for name, _, info in downloads}
    (out_dir / "sources.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest
