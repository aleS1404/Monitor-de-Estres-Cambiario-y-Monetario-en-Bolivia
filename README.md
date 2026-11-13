# Monitor de estrés cambiario y monetario de Bolivia

Proyecto de **Procesos Estocásticos y Series de Tiempo (DAT 262)**: pipeline de datos del BCB + análisis por capítulo del libro + tablero Streamlit + informe.

```
Excel BCB ──────────► bcb_pipeline ─► data/processed ─┐
PDF BCB / DolarApi ─► bcb_pipeline ─► data/p2p ───────┼─► stress_monitor ─► tablero · informe · notebooks
P2P histórico + TCO diario ─► data/external ──────────┘
```

## Inicio rápido (todo desde la carpeta raíz)

```bash
pip install -r requirements.txt
python -m bcb_pipeline download --latest    # obtiene el Excel más reciente del BCB
python -m bcb_pipeline build                # regenera data/processed desde data/raw
python -m bcb_pipeline fetch-history        # P2P histórico y TCO diario con manifiesto
python -m stress_monitor.report              # genera reports/INFORME.md + figuras (~1-2 min)
streamlit run app/streamlit_app.py           # tablero
python -m pytest -q                          # suite completa
```
Con `make`: `make install | data | report | notebooks | app | test`.

Los Excel descargados en `data/raw/` no se versionan; el repositorio sí incluye los datos procesados y el informe generado. Las dos series diarias originales y su procedencia están en [`data/external/`](data/external/README.md).

## Qué incluye

| Carpeta | Contenido |
|---|---|
| `bcb_pipeline/` | Descarga de los Excel del BCB, parseo ancho→largo, recolector P2P (DolarApi), importador del PDF de activos virtuales |
| `stress_monitor/` | `stationarity` (cap. 1-2, 5) · `markov` (cap. 3) · `forecasting` (cap. 4, 6) · `gap` (cap. 5) · `simulation` (cap. 7) · `report` |
| `app/streamlit_app.py` | Tablero de 7 pantallas: semáforo, brecha, reservas y depósitos, inflación, simulador, alertas, metodología |
| `notebooks/` | 6 notebooks por capítulo, **ya ejecutados** (se regeneran con `python notebooks/build_notebooks.py`) |
| `reports/` | `INFORME.md` generado con cifras reales, `results.json`, `figures/` |
| `docs/GUION_PRESENTACION.md` | Guion de la presentación y preguntas probables |
| `.github/workflows/` | Actualización semanal de datos y recolector P2P horario (opcional) |

## Comandos del pipeline

```bash
python -m bcb_pipeline download --latest            # último Excel (basta para la serie mensual 1987→hoy)
python -m bcb_pipeline download --since-year 2023   # panel semanal/diario
python -m bcb_pipeline update                       # download + build (semanal)
python -m bcb_pipeline collect --loop               # guarda P2P/oficial cada hora en data/p2p/p2p.sqlite
python -m bcb_pipeline collect --csv-only --csv data/p2p/quotes.csv   # modo nube
python -m bcb_pipeline import-pdf HISTORICO.pdf     # tabla de activos virtuales del BCB → SQLite
python -m bcb_pipeline check-layout data/raw/ARCHIVO.xlsx
python -m bcb_pipeline fetch-history                # actualiza mediana P2P y TCO diario
```

## Hallazgos (comparaciones seleccionadas hasta sep-2026; datos mensuales disponibles hasta oct-2026)

1. **Efecto de valoración.** La bolivianización de depósitos medida al tipo de cambio vigente cae de 92,1% a 88,3% (sep-2025→sep-2026), pero **a tipo constante sube de 92,1% a 92,9%** y los depósitos en dólares no aumentaron (2.654→2.616 MM USD). La caída es contable. El índice de estrés usa la versión neutral.
2. **Tres regímenes cambiarios** visibles en el Excel: fijo 6,96, «referencial» (dic-2025→may-2026) y oficial flexible (jun-2026→). El BCB convirtió sus cuadros a 6,96 hasta mayo (no al referencial).
3. **Markov:** estados persistentes (Estable 0,92 de permanencia mensual); la cadena de primer orden se rechaza frente a orden 2, así que es una aproximación.
4. **El índice sin brecha no capta** la tensión cambiaria de dic-2025→may-2026: esa señal vive en el mercado paralelo. El índice mantiene dos componentes en toda la historia; la brecha se analiza por separado.
5. **SARIMA vs. ingenuo (H4):** gana en base monetaria y depósitos; **no gana en reservas**; en IPC gana Holt-Winters. Los IC 95% de reservas e IPC cubren menos de lo nominal.

## Estado honesto: qué está probado y qué no

| Componente | Estado |
|---|---|
| Parseo del Excel, análisis, informe, notebooks | ✅ Probado con Excel reales descargados del BCB |
| Tablero | ✅ Las 7 pantallas ejecutan sin excepciones (AppTest). ⚠️ No se hizo revisión visual en navegador |
| Importador PDF del BCB | ✅ Probado con `HISTORICO.pdf` completo (15 filas de 2024); no se encontraron PDF históricos verificables de 2025-2026 |
| Descarga en vivo del BCB | ✅ Probada: último Excel y 50 archivos desde 2025 según el listado disponible; cobertura semanal de 2025 incompleta |
| Recolector DolarApi | ✅ JSON real de `/binance` y `/oficial` verificado; una captura real guardada |
| GitHub Actions | ✅ Recolector P2P horario ejecutado y CSV actualizado; verificar futuras ejecuciones periódicas |
| **Brecha oficial–paralelo (H1, H5, H3 formal)** | ✅ Serie observada de mediana P2P de paralelo.bo (830 fechas, ago-2024 a nov-2026) y TCO diario del BCB desde jun-2026. Resultados en [`reports/INFORME.md`](reports/INFORME.md). No se usa DEMO en el informe |
| GARCH | No implementado (extensión opcional fuera del temario) |

## Historial P2P y reproducibilidad

`python -m bcb_pipeline fetch-history` guarda las series y `sources.json` (URL, fecha, SHA-256, cobertura). La mediana P2P histórica de [paralelo.bo](https://paralelo.bo/api/v1/historical.csv) tiene licencia CC BY 4.0; se atribuye a paralelo.bo. Es un precio anunciado reconstruido retrospectivamente antes de mayo-2026; su [metodología](https://paralelo.bo/metodologia) cambió el 4-sep-2026. El TCO diario procede del [BCB](https://www.bcb.gob.bo/grafico_evolutivo/download.php?serie=tipo_de_cambio&format=csv). Antes del 29-jun-2026 ese CSV contiene 6,86 de compra, que no se usa como 6,96 de venta.

El PDF del BCB y el recolector DolarApi son fuentes separadas: no se mezclan con la mediana histórica. H1 usa la brecha del régimen flexible; H3 compara la misma metodología de la mediana entre 4-may y 3-sep-2026; H5 usa retornos hábiles desde julio-2026. Importa PDF adicionales, si aparecen, con `python -m bcb_pipeline import-pdf ARCHIVO.pdf`; el recolector propio sigue con `python -m bcb_pipeline collect --loop`.

## Limitaciones y ética

- El régimen flexible empieza en jun-2026; los análisis diarios aún son exploratorios y sensibles a la metodología y al horario de publicación.
- El simulador de riesgo estima σ con el TCO diario desde ago-2026; su rango es indicativo.
- Los estados son relativos a la historia (percentiles), no un diagnóstico de crisis.
- Datos recientes del BCB son preliminares. Respeta términos de uso y pausas al descargar.
- **Herramienta académica; no es asesoría financiera ni predicción.**
