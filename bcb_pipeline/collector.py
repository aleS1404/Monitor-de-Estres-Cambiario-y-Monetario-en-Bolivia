"""Recolector del dólar P2P (Binance, vía DolarApi) y oficial. Guarda en SQLite.

DolarApi solo entrega la cotización ACTUAL; el historial lo construimos nosotros
consultando cada hora. Respuesta verificada de /v1/dolares/binance:
  {"moneda":"USD","casa":"binance","nombre":"Binance","compra":11.9,"venta":11.93,
   "fechaActualizacion":"2026-11-11T21:01:22.572Z"}
"""
from __future__ import annotations

import datetime as dt
import sqlite3
import time
from pathlib import Path

import pandas as pd
import requests

URL_P2P = "https://bo.dolarapi.com/v1/dolares/binance"
URL_OFICIAL = "https://bo.dolarapi.com/v1/dolares/oficial"
DEFAULT_DB = Path("data/p2p/p2p.sqlite")

SCHEMA = """
CREATE TABLE IF NOT EXISTS quotes(
  ts_utc TEXT PRIMARY KEY,
  p2p_compra REAL, p2p_venta REAL, p2p_updated TEXT,
  of_compra REAL, of_venta REAL, of_updated TEXT);
CREATE TABLE IF NOT EXISTS bcb_usdt(
  date TEXT PRIMARY KEY,
  usdt_compra REAL, usdt_venta REAL, btc_usd REAL, eth_usd REAL, source TEXT);
"""


def connect(db_path: Path = DEFAULT_DB) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.executescript(SCHEMA)
    return con


def _get(url: str) -> dict:
    r = requests.get(url, timeout=20, headers={"User-Agent": "proyecto-academico-series-tiempo"})
    r.raise_for_status()
    return r.json()


def _num(d: dict, key: str):
    v = d.get(key)
    return float(v) if isinstance(v, (int, float)) else None


def collect_once(db_path: Path | None = DEFAULT_DB, csv_path: Path | None = None) -> dict:
    """Guarda una observación. Si el oficial falla, igual guarda el P2P (y viceversa)."""
    p2p, of = {}, {}
    try:
        p2p = _get(URL_P2P)
    except Exception as e:  # noqa: BLE001
        print(f"! P2P: {e}")
    try:
        of = _get(URL_OFICIAL)
    except Exception as e:  # noqa: BLE001
        print(f"! oficial: {e}")
    if not p2p and not of:
        raise RuntimeError("Ninguna fuente respondió")
    ts = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    row = (ts, _num(p2p, "compra"), _num(p2p, "venta"), p2p.get("fechaActualizacion"),
           _num(of, "compra"), _num(of, "venta"), of.get("fechaActualizacion"))
    cols = ["ts_utc", "p2p_compra", "p2p_venta", "p2p_updated", "of_compra", "of_venta", "of_updated"]
    if db_path:
        with connect(db_path) as con:
            con.execute("INSERT OR REPLACE INTO quotes VALUES (?,?,?,?,?,?,?)", row)
    if csv_path:   # modo nube: acumula en un CSV versionable
        csv_path = Path(csv_path); csv_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([row], columns=cols).to_csv(csv_path, mode="a", header=not csv_path.exists(), index=False)
    print(f"{ts} | P2P {row[1]}/{row[2]} | oficial {row[4]}/{row[5]}")
    return dict(zip(["ts_utc", "p2p_compra", "p2p_venta", "p2p_updated", "of_compra", "of_venta", "of_updated"], row))


def collect_loop(db_path: Path = DEFAULT_DB, every_seconds: int = 3600) -> None:
    while True:
        try:
            collect_once(db_path)
        except Exception as e:  # noqa: BLE001
            print(f"! {e}")
        time.sleep(every_seconds)


def export_csv(db_path: Path = DEFAULT_DB, csv_path: Path = Path("data/p2p/quotes.csv")) -> Path:
    with connect(db_path) as con:
        df = pd.read_sql("SELECT * FROM quotes ORDER BY ts_utc", con)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)
    return csv_path
