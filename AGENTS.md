# Instrucciones para agentes (Codex / Claude Code)

Proyecto universitario (DAT 262): monitor de estrés cambiario y monetario de Bolivia.
Todo se ejecuta desde la carpeta raíz.

## Comandos
- Instalar: `pip install -r requirements.txt` · Tests: `python -m pytest -q`
- Datos: `python -m bcb_pipeline download --latest | --since-year 2023` · `build` · `update`
- P2P: `python -m bcb_pipeline collect [--loop]` · `import-pdf ARCHIVO.pdf`
- Informe: `python -m stress_monitor.report [--rapido]` · Tablero: `streamlit run app/streamlit_app.py`
- Notebooks: `python notebooks/build_notebooks.py`

## Reglas
- Fuente BCB: https://www.bcb.gob.bo/?q=estad-sticas-semanales (paginado `&page=N`, más nuevo primero). NUNCA adivinar
  nombres de archivo; extraer links del HTML. Mínimo 1,5 s entre descargas; no paralelizar.
- Cada Excel trae TODA la historia mensual; solo semanal/diario requiere varios archivos.
- Si el BCB bloquea (403/timeout), no usar trucos: avisar y pedir descarga manual a `data/raw/Semanal_AAAA_SS.xlsx`.
- Si `check-layout` reporta filas movidas, actualizar `KEY_VARIABLES` en `bcb_pipeline/parse.py`.
- **Bolivianización:** NUNCA usar la serie a tipo de cambio vigente como señal de estrés (efecto de valoración). Usar
  `data.bolivianizacion_neutral_change`. La fila 95 del Excel usa otra definición: no mezclar.
- **Datos DEMO** (`stress_monitor/demo.py`) son simulados: jamás presentarlos como reales ni usarlos en el informe.
- Los resultados de H1, H3 (formal) y H5 requieren ≥30 días de P2P real; no inventarlos.
- Mantener los avisos «no es asesoría financiera» en el simulador y el tablero.
- No editar `data/raw/` a mano. `data/processed/` y `reports/` se regeneran.

## Tareas abiertas sugeridas
1. Validar `download --latest` contra el sitio real y ajustar `LINK_RE` si cambió el HTML.
2. Importar los PDF de activos virtuales de 2025-2026 y verificar el parseo con el PDF completo.
3. Verificar el JSON de `https://bo.dolarapi.com/v1/dolares/oficial` (se asume igual al de /binance).
4. Con ≥30 días de P2P: regenerar el informe y completar H1/H3/H5.
5. Extensión opcional: GARCH (paquete `arch`) para volatilidad condicional del paralelo.
