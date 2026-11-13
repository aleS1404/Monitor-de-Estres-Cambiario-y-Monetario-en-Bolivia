import pandas as pd

from bcb_pipeline import collector
from bcb_pipeline.virtual_assets import parse_text
from stress_monitor import data

PDF_TXT = """FECHA TETHER BITCOIN ETHEREUM
17/10/2024 10,40 10,62 67.372,26 2.603,70
18/10/2024 10,29 10,65 67.535,72 2.607,43
texto basura 123
"""


def test_parse_pdf_activos_virtuales():
    df = parse_text(PDF_TXT)
    assert len(df) == 2
    r = df.iloc[0]
    assert r.usdt_compra == 10.40 and r.usdt_venta == 10.62 and r.btc_usd == 67372.26 and r.eth_usd == 2603.70


def test_collector_csv_y_lectura(tmp_path, monkeypatch):
    def fake_get(url):
        base = {"moneda": "USD", "fechaActualizacion": "2026-11-11T21:01:22.572Z"}
        return {**base, "compra": 11.9, "venta": 11.93} if "binance" in url else {**base, "compra": 11.8, "venta": 11.81}
    monkeypatch.setattr(collector, "_get", fake_get)
    csv = tmp_path / "q.csv"
    row = collector.collect_once(None, csv)
    assert row["p2p_venta"] == 11.93 and row["of_venta"] == 11.81
    collector.collect_once(None, csv)
    assert len(pd.read_csv(csv)) == 2
    col, pdf = data.load_p2p(db_path=tmp_path / "no.sqlite", csv_path=csv)
    assert len(col) == 1 and abs(col["p2p_venta"].iloc[0] - 11.93) < 1e-9 and pdf.empty


def test_collector_tolera_caida_de_una_fuente(tmp_path, monkeypatch):
    def fake_get(url):
        if "oficial" in url:
            raise RuntimeError("caído")
        return {"compra": 11.9, "venta": 11.93, "fechaActualizacion": "x"}
    monkeypatch.setattr(collector, "_get", fake_get)
    row = collector.collect_once(tmp_path / "d.sqlite")
    assert row["p2p_venta"] == 11.93 and row["of_venta"] is None


def test_sqlite_y_pdf_alimentan_la_brecha(tmp_path):
    db = tmp_path / "p.sqlite"
    with collector.connect(db) as con:
        for i, d in enumerate(pd.date_range("2024-10-17", periods=40)):
            con.execute("INSERT INTO bcb_usdt VALUES (?,?,?,?,?,?)", (d.strftime("%Y-%m-%d"), 10.4, 10.6 + i * .01, 1, 1, "t"))
    col, pdf = data.load_p2p(db_path=db, csv_path=tmp_path / "x.csv")
    assert col.empty and len(pdf) == 40
    m = data.load_monthly()
    g = data.build_gap(m, None, col, pdf)
    assert len(g) > 30 and (g["brecha_pct"] > 40).all()      # 10,6 / 6,96 − 1 ≈ +52%
