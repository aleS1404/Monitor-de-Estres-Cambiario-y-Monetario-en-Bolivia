# Fuentes diarias observadas

- `paralelo_bo_historical.csv`: mediana diaria de anuncios P2P en Bs/USD, [paralelo.bo](https://paralelo.bo/api/v1/historical.csv), licencia [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Atribución: paralelo.bo. Se guarda el CSV original; el proyecto calcula retornos y brecha. No representa una transacción ejecutada ni la cotización de Binance. El tramo previo al lanzamiento del sitio es una reconstrucción histórica; la metodología cambió el 4 de septiembre de 2026 ([metodología](https://paralelo.bo/metodologia)).
- `bcb_tco_daily.csv`: [exportación diaria del BCB](https://www.bcb.gob.bo/grafico_evolutivo/download.php?serie=tipo_de_cambio&format=csv). El análisis usa el tramo desde el 29 de junio de 2026; el valor 6,86 anterior corresponde al tipo de compra fijo y no sustituye el tipo de venta 6,96.
- `sources.json`: URL, fecha de descarga UTC, SHA-256 y rango de cada archivo. Regenerar los tres archivos con `python -m bcb_pipeline fetch-history`.

La brecha se calcula con una única definición del paralelo por análisis. El PDF del BCB y las capturas de DolarApi se conservan como fuentes separadas y no rellenan huecos de la mediana histórica. H1 se estima desde el régimen flexible. H3 compara retornos de la mediana del 4 de mayo al 3 de septiembre de 2026. H5 usa retornos hábiles desde julio de 2026.
