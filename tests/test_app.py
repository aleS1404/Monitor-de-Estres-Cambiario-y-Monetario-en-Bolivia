"""Prueba de humo del tablero: cada pantalla debe renderizar sin excepciones."""
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

PAGES = ["Semáforo del sistema", "Brecha cambiaria", "Reservas y depósitos", "Inflación",
         "Simulador de riesgo", "Alertas", "Metodología"]


@pytest.fixture(scope="module")
def app():
    at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"), default_timeout=300)
    at.run()
    return at


@pytest.mark.parametrize("page", PAGES)
def test_pagina_sin_excepciones(app, page):
    app.sidebar.radio[0].set_value(page).run()
    assert not app.exception, [e.value for e in app.exception]


def test_demo_brecha(app):
    app.sidebar.toggle[0].set_value(True)
    app.sidebar.radio[0].set_value("Brecha cambiaria").run()
    assert not app.exception, [e.value for e in app.exception]
    assert any("vida media" in m.label.lower() for m in app.metric)
    app.sidebar.toggle[0].set_value(False).run()
