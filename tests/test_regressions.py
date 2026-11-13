"""Regresiones detectadas al ejecutar el pipeline completo en Windows."""
import io
import json
import shutil
from contextlib import redirect_stdout
from pathlib import Path

import pandas as pd
import pytest

from bcb_pipeline import virtual_assets
from bcb_pipeline.build import build
from stress_monitor import data, report


def test_recolector_agrupa_por_fecha_boliviana(tmp_path):
    csv = tmp_path / "quotes.csv"
    pd.DataFrame([
        {"ts_utc": "2026-11-13T03:48:35+00:00", "p2p_compra": 11.9,
         "p2p_venta": 11.95, "of_compra": 11.7, "of_venta": 11.7}
    ]).to_csv(csv, index=False)
    quotes, _ = data.load_p2p(db_path=tmp_path / "missing.sqlite", csv_path=csv)
    assert list(quotes.index) == [pd.Timestamp("2026-11-12")]


def test_build_termina_con_consola_cp1252(tmp_path):
    sample = max(Path("data/raw").glob("Semanal_*.xlsx"), default=None)
    if sample is None:
        pytest.skip("sin Excel descargado")
    raw = tmp_path / "raw"
    raw.mkdir()
    shutil.copy2(sample, raw / sample.name)
    output = io.BytesIO()
    stream = io.TextIOWrapper(output, encoding="cp1252")
    with redirect_stdout(stream):
        paths = build(raw, tmp_path / "processed")
    stream.flush()
    assert paths["monthly_key"].exists()
    assert b"Mensual:" in output.getvalue()


def test_importacion_pdf_termina_con_consola_cp1252(tmp_path, monkeypatch):
    text = "17/10/2024 10,40 10,62 67.372,26 2.603,70"
    monkeypatch.setattr(virtual_assets, "read_pdf_text", lambda _: text)
    output = io.BytesIO()
    stream = io.TextIOWrapper(output, encoding="cp1252")
    with redirect_stdout(stream):
        n = virtual_assets.import_pdfs([tmp_path / "HISTORICO.pdf"], tmp_path / "p2p.sqlite")
    stream.flush()
    assert n == 1
    assert b"2024-10-17" in output.getvalue()


def test_informe_json_utf8_y_estado_de_hipotesis(tmp_path):
    result = report.run(tmp_path, validate=False)
    saved = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    markdown = (tmp_path / "INFORME.md").read_text(encoding="utf-8")
    assert saved["ultimo_mes"] == result["ultimo_mes"]
    assert "Δlog" in (tmp_path / "results.json").read_text(encoding="utf-8")
    if saved["brecha"]["n_dias"] < 30:
        assert "H5 | El paralelo se adelanta al oficial | Pendiente" in markdown
