import datetime as dt
from pathlib import Path

import pytest

from bcb_pipeline.download import extract_links
from bcb_pipeline.parse import classify_column, parse_workbook, validate_layout

HTML = '''
<a href="https://www.bcb.gob.bo/webdocs/05_estadisticassemanales/Semanal%2045_2026%20%281%29.xlsx">x</a>
<a href="https://www.bcb.gob.bo/webdocs/05_estadisticassemanales/Semanal%2044_2026.xlsx">x</a>
<a href="/otra/cosa.xlsx">no</a>
'''


def test_extract_links():
    files = extract_links(HTML)
    assert [(f.year, f.week) for f in files] == [(2026, 45), (2026, 44)]
    assert files[0].filename == "Semanal_2026_45.xlsx"
    assert " " not in files[0].url


def test_classify_column():
    d = dt.datetime(2026, 10, 27)
    assert classify_column(dt.datetime(2026, 9, 30), None)[0] == "M"
    assert classify_column(dt.datetime(1987, 12, 31), None)[0] == "A"
    assert classify_column("Semana 3", d)[0] == "W"
    assert classify_column(None, d)[0] == "D"
    assert classify_column(None, None)[0] is None


SAMPLES = sorted(Path("data/raw").glob("Semanal_*.xlsx"))


@pytest.mark.skipif(not SAMPLES, reason="sin Excel descargado")
def test_parse_sample():
    long, cat = parse_workbook(SAMPLES[-1])
    assert validate_layout(cat) == []
    assert {"A", "M", "W", "D"} <= set(long.freq)
    assert long[(long.row == 141) & (long.freq == "M")].shape[0] > 400
