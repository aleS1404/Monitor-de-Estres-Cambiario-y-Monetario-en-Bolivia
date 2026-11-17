# Monitor de estrés cambiario y monetario de Bolivia

## Informe académico integral del proyecto DAT 262

**Asignatura:** Procesos Estocásticos y Series de Tiempo (DAT 262).

**Fecha de redacción:** 17 de noviembre de 2026.

**Corte de los resultados reproducidos aquí:** Excel del BCB hasta octubre de 2026; CSV diarios descargados el 13 de noviembre de 2026. Las cifras no representan una actualización al 17 de noviembre.
**Código y datos procesados:** repositorio del proyecto; resultados numéricos en [`results.json`](results.json); figuras e informe generado en [`INFORME.md`](INFORME.md).

> **Alcance:** investigación aplicada y herramienta docente. Los estados, pronósticos, probabilidades y escenarios son estimaciones condicionadas a los datos y supuestos. **No constituyen asesoría financiera.** Ningún dato de `stress_monitor/demo.py` se usa como observación ni como resultado de este informe.

## Resumen

El proyecto integra estadísticas monetarias y cambiarias del Banco Central de Bolivia (BCB), una serie histórica observada de anuncios P2P de USDT y técnicas de procesos estocásticos para estudiar cómo se manifiesta la tensión cambiaria en distintas variables. El problema central es que un tipo de cambio oficial estable puede coexistir con presión sobre las reservas y con un precio P2P distinto. En el período estudiado se distinguen un tipo oficial de venta de Bs 6,96, la publicación de un valor referencial desde diciembre de 2025 y el uso del tipo de cambio oficial diario (TCO) desde el 29 de junio de 2026. El [BCB documenta el valor referencial](https://www.bcb.gob.bo/?q=node%2F238466) y la [entrada en vigencia del nuevo TCO](https://www.bcb.gob.bo/?q=node%2F240202).

La contribución técnica comprende: descarga y validación de Excel semanales; consolidación mensual, semanal y diaria; registro de versiones; importación de PDF de activos virtuales; captura de cotizaciones de DolarApi; incorporación de una mediana P2P histórica con procedencia y licencia; análisis de estacionariedad, autocorrelación y espectro; clasificación de estados con cadenas de Markov; AR(1) de la brecha; comparación de volatilidad; correlación cruzada y pruebas de Granger; descomposición, Holt-Winters y SARIMA; simulaciones Monte Carlo; tablero Streamlit, notebooks e informe generado.

Los datos guardados al 13 de noviembre contienen **454 meses** (enero de 1989 a octubre de 2026), **830 fechas** de mediana P2P (agosto de 2024 a noviembre de 2026) y **138 fechas** de TCO utilizadas desde junio de 2026. Los resultados más destacados son: (i) la caída de una medida de bolivianización calculada con el tipo vigente en 2026 se explica principalmente por la conversión de los saldos en bolivianos a dólares; (ii) el índice monetario, construido solo con reservas y cambio de bolivianización neutralizado, clasifica octubre de 2026 como «Estable», pero no captura toda la tensión observada en el P2P; (iii) para el régimen flexible, el AR(1) de la brecha arroja una vida media estimada de **4,0 días**; (iv) la desviación estándar del retorno diario P2P es **2,39 veces** la del período anterior en una ventana con metodología comparable; (v) en retornos hábiles, la mayor correlación cruzada se observa cuando el P2P antecede un día al TCO. Este último resultado es **predictivo y descriptivo, no causal**.

## 1. Problema económico, preguntas y objetivos

### 1.1. Problema de investigación

La presión sobre un régimen cambiario no siempre se refleja de inmediato en su cotización oficial. Si el precio oficial está administrado, parte del ajuste puede aparecer como pérdida de reservas, menor disponibilidad de divisas, operaciones a precios distintos o una brecha entre referencias. La literatura del FMI utiliza justamente el tipo de cambio y las reservas como canales alternativos para observar presión cambiaria; ese marco orienta la interpretación económica, **aunque el índice de este proyecto no es el índice formal de presión cambiaria del FMI** ([FMI, metodología de presión cambiaria](https://www.elibrary.imf.org/view/journals/007/2010/040/article-A001-en.xml)).

La pregunta general es: **¿qué señales monetarias y cambiarias permiten describir la tensión de Bolivia y cómo cambiaron al modificarse el régimen de cotización oficial?** De ella se desprenden cinco preguntas: ¿persiste la brecha P2P-oficial?, ¿cuánto duran sus desviaciones?, ¿cambió la volatilidad del P2P?, ¿el P2P precede estadísticamente al TCO?, ¿aportan los modelos de series de tiempo más que un pronóstico ingenuo?

### 1.2. Objetivo general y objetivos específicos

**Objetivo general.** Construir un monitor reproducible que convierta fuentes públicas en indicadores, estados, contrastes y escenarios cuantitativos, con procedencia verificable y advertencias sobre su interpretación.

**Objetivos específicos:** (1) consolidar la historia del BCB sin confundir frecuencias ni versiones; (2) separar precio oficial, referencial, TCO y medidas P2P; (3) construir una señal monetaria comparable en el tiempo; (4) estimar y contrastar H1-H5; (5) comparar SARIMA con referencias simples mediante validación temporal; (6) comunicar resultados y limitaciones en un tablero e informe reproducibles.

### 1.3. Alcance de la inferencia

El trabajo es **observacional**. No identifica efectos causales de una decisión del BCB sobre precios P2P, reservas o inflación. La fecha de cambio de régimen es un corte analítico, pero el entorno económico puede cambiar simultáneamente por otras razones. El conjunto P2P contiene anuncios y agregaciones de plataformas, no todas las transacciones cambiarias. Los umbrales de «Tensión» y «Crisis» son convenciones estadísticas definidas por el proyecto, no declaraciones oficiales.

## 2. Marco teórico económico

### 2.1. Tipo de cambio, régimen y mercado de divisas

El tipo de cambio nominal (E_t), expresado aquí en **bolivianos por dólar (Bs/USD)**, es el precio en moneda local de una unidad de USD. Un aumento de (E_t) representa depreciación nominal del boliviano bajo esta convención. Deben distinguirse el **precio de compra** (lo que paga quien compra dólares a un cliente), el **precio de venta** (lo que cobra al venderlos), una referencia estadística y un precio de un mercado P2P. Son objetos económicos diferentes; compartir la unidad Bs/USD no los vuelve intercambiables.

El proyecto observa tres etapas: (a) tipo de venta del Bolsín utilizado como referencia fija de Bs 6,96 hasta mayo de 2026; (b) valor referencial de venta publicado entre diciembre de 2025 y mayo de 2026, coexistente con el tipo oficial administrado; (c) TCO diario en el régimen flexible desde el 29 de junio de 2026. El [BCB explica que el valor referencial se basaba en operaciones de entidades financieras con clientes](https://www.bcb.gob.bo/?q=node%2F238466) y la [cotización oficial diaria del nuevo régimen](https://www.bcb.gob.bo/bcb_tco_publico_ultima_cotizacion.php). El código usa estas fechas operativas para segmentar muestras; las cifras del TCO del informe terminan el **13 de noviembre de 2026**.

Un mercado P2P de USDT/BOB puede generar una referencia de precio de acceso a dólares digitales, pero **USDT no es idéntico a un depósito bancario en USD ni a un billete de dólar**. Hay diferencias de emisor, liquidez, plataforma, límites, riesgo de contraparte y modalidad de liquidación. La mediana de [paralelo.bo](https://paralelo.bo/metodologia) agrega anuncios P2P y publica un punto medio entre las medianas de compra y venta; el TCO del BCB se basa en operaciones del sistema financiero formal y, en la serie utilizada, corresponde al lado de compra. Por ello, la brecha definida más adelante es una **distancia entre referencias de distintos mercados y lados de cotización**, no una oportunidad de arbitraje ejecutable al precio mostrado.

### 2.2. Reservas internacionales y capacidad de respuesta externa

Las **reservas internacionales brutas (RIB)** son activos externos bajo control de la autoridad monetaria y disponibles para necesidades de balanza de pagos, intervención cambiaria y otros fines. El [glosario del BCB](https://www.bcb.gob.bo/webdocs/seccioneducativa/GLOSARIO%20DE%20TE%CC%81RMINOS%20ECONO%CC%81MICO%20FINANCIEROS%20.pdf) distingue RIB de **reservas internacionales netas (RIN)**, que restan obligaciones externas de corto plazo; el [manual BPM6 del FMI](https://data.imf.org/-/media/iData/External-Storage/Documents/73FBCD5B6CDE4D289C60B9B0CAA40622/en/2-bpm6.pdf) aporta el marco internacional de activos de reserva. En el proyecto, RIB es la variable principal del índice, SARIMA, periodograma y Monte Carlo; RIN se conserva en la base y ofrece contexto, pero no se suma al índice para evitar duplicar información muy relacionada.

Una caída de reservas **puede** ser compatible con presión de divisas, pero también puede reflejar pagos, valoración de activos, decisiones de cartera u otros movimientos. El monitor no atribuye automáticamente cada descenso a intervención cambiaria. Por eso la señal usa un cambio interanual de RIB estandarizado, no una afirmación causal sobre el destino de las reservas.

### 2.3. Base monetaria, depósitos y bolivianización

La **base monetaria** representa pasivos monetarios de alto poder de creación de dinero y se expresa en millones de bolivianos en los cuadros del BCB. Su evolución importa para liquidez y política monetaria; el proyecto la pronostica, pero no supone una relación mecánica o contemporánea con inflación o tipo de cambio.

Los **depósitos en moneda nacional (MN)** y **en moneda extranjera (ME)** expresan la composición por moneda del sistema financiero. Una medida intuitiva de bolivianización es la proporción de saldos en MN dentro del total, una vez expresados ambos en la misma unidad. En los cuadros usados, las filas de depósitos MN y ME están denominadas en **millones de USD**: el saldo MN es una conversión de bolivianos a dólares y puede bajar en USD sin que haya disminuido la cantidad original de bolivianos. El proyecto reconstruye el saldo nominal en Bs multiplicando el dato MN expresado en USD por el tipo de conversión empleado para ese mes. La medida calculada a tipo vigente es:

$$
B_t^{vig}=100\frac{MN_t^{USD}}{MN_t^{USD}+ME_t^{USD}}.
$$

Para comparar dos meses con una misma valoración se usa un tipo $E_0$ común:

$$
B_t(E_0)=100\frac{MN_t^{Bs}}{MN_t^{Bs}+E_0 ME_t^{USD}},\qquad
\Delta_6 B_t^{neutral}=B_t(E_{t-6})-B_{t-6}(E_{t-6}).
$$

Así, **ambos saldos se valoran al tipo de cambio del inicio de la ventana de seis meses**. El índice usa $-\Delta_6 B_t^{neutral}$: una reducción de la proporción MN por cambios de composición eleva la señal de tensión, mientras un mero cambio del denominador cambiario no la eleva. La función exacta es `data.bolivianizacion_neutral_change`. La serie de bolivianización publicada por el BCB en la **fila 95** emplea una definición que no coincide exactamente con el cociente reconstruido de las **filas 92 y 94**; se describe por separado y **no se mezcla** en esta comparación. La diferencia de definición concreta no se ha verificado documentalmente: no se le atribuye una causa específica.

En la comparación guardada entre septiembre de 2025 y octubre de 2026, $B^{vig}$ calculada con las filas 92/94 pasa de **92,1 % a 88,5 %**, mientras la versión a tipo constante Bs 6,96 pasa de **92,1 % a 93,0 %**. El saldo ME pasa de **2.654 a 2.578 millones de USD**. En ese par de fechas, la caída de $B^{vig}$ no evidencia por sí sola un traslado de depósitos hacia USD: la valoración explica el signo divergente. Es una interpretación contable de la construcción de la variable, no una prueba de todos los flujos de ahorro de la economía.

### 2.4. Precios, inflación y tipo de cambio real

El **índice de precios al consumidor (IPC, base 2016=100)** mide la evolución de precios de una canasta representativa; el [documento metodológico del INE](https://www.ine.gob.bo/index.php/descarga/171/metodologia/37244/documento-metodologico-ipc-2016.pdf) define el índice y la inflación como su variación porcentual. El proyecto utiliza el nivel mensual del IPC para descomposición y SARIMA, y muestra por separado la inflación interanual publicada por el BCB:

$$
\pi_{12,t}=100\left(\frac{IPC_t}{IPC_{t-12}}-1\right).
$$

Al proyectar el IPC, el tablero calcula también la inflación a 12 meses **implícita en el pronóstico**, que no es un pronóstico independiente estimado directamente sobre la tasa. Una asociación entre depreciación e inflación sería plausible por costos de importación y expectativas, pero este proyecto **no estima un coeficiente causal de traspaso cambiario**.

El **índice de tipo de cambio real (TCR, base diciembre de 2022=100)** está conservado como variable contextual del BCB. En teoría, un tipo real ajusta el nominal por precios relativos de países; una variación puede informar sobre competitividad de precios bajo una convención de índice determinada. El código no recalcula el TCR ni lo usa para el semáforo, AR(1), H3 o H5. Debe consultarse su definición exacta en el BCB antes de inferir el sentido económico de una subida del índice.

### 2.5. Brecha cambiaria y transmisión de información

La brecha del proyecto se define sobre observaciones con fecha común:

$$
G_t=100\left(\frac{P^{P2P}_t}{E^{ref}_t}-1\right),
$$

donde $P^{P2P}_t$ es la mediana histórica de anuncios USDT/BOB y $E^{ref}_t$ es la referencia BCB según el régimen. Antes del TCO, la referencia se deriva de los Excel del BCB; desde el 29 de junio de 2026 se superpone el TCO diario. Se descarta el tramo fijo de **Bs 6,86 de compra** del CSV histórico del TCO para no usarlo como si fuese la venta fija **Bs 6,96**. Una brecha positiva indica que la referencia P2P excede la oficial elegida; su magnitud también recoge diferencias entre instrumentos, lados de cotización, horarios y fricciones de acceso. El código no convierte esa brecha en una medida exacta de «prima de mercado negro» ni la emplea como componente del índice mensual de Markov, porque aparece recién desde 2024 y alteraría el número de componentes a mitad de la historia.

La hipótesis de adelanto H5 se refiere a **precedencia estadística**. El TCO se publica con calendario de días hábiles y una fecha de corte distinta de su vigencia, mientras la mediana P2P se actualiza con mayor frecuencia; el [BCB muestra fecha de corte y vigencia](https://www.bcb.gob.bo/bcb_tco_publico_evolutivo.php) y el [proveedor P2P describe sus actualizaciones](https://paralelo.bo/metodologia). Una correlación en $k=1$ puede originarse simplemente en ese desfase de publicación. Se requieren controles adicionales, eventos y convenciones de fecha homogéneas para sostener una interpretación económica más fuerte.

## 3. Fuentes, variables y unidades de observación

### 3.1. Fuentes primarias y archivos del proyecto

| Fuente | Archivo local o tabla | Cobertura guardada | Papel en el análisis | Precaución |
|---|---|---|---|---|
| [BCB, Estadísticas Semanales](https://www.bcb.gob.bo/?q=estad-sticas-semanales) | `data/raw/Semanal_AAAA_SS.xlsx`, `data/processed/*` | 454 meses modelados, ene-1989 a oct-2026; panel semanal/diario reciente | Macrovariables, referencia cambiaria, validación de episodios | Los Excel brutos no se versionan; la historia mensual está completa en el Excel más reciente de la descarga local |
| [BCB, TCO diario](https://www.bcb.gob.bo/bcb_tco_publico_ultima_cotizacion.php) | `data/external/bcb_tco_daily.csv` | Exportación original: 2.143 filas, ene-2021 a nov-2026; se usan 138 desde 29-jun-2026 | Denominador diario post-cambio de la brecha y volatilidad del simulador | Antes del cambio, 6,86 corresponde a compra fija, no a venta 6,96; TCO y P2P tienen distinta convención de precio |
| [paralelo.bo, histórico](https://paralelo.bo/api/v1/historical.csv) | `data/external/paralelo_bo_historical.csv` | 830 fechas, 6-ago-2024 a 13-nov-2026 | Mediana P2P para H1, H3 y H5 | Anuncios, no transacciones; tramo anterior al lanzamiento reconstruido; cambio metodológico 4-sep-2026; CC BY 4.0, atribución: paralelo.bo |
| [BCB, PDF de activos virtuales](https://www.bcb.gob.bo/webdocs/activos_virtuales/HISTORICO.pdf) | tabla `bcb_usdt` de `data/p2p/p2p.sqlite` | PDF histórico validado: 15 fechas de oct-nov 2024 | Comprobación e importador; respaldo alternativo si no existe serie externa | Tether es promedio ponderado por volumen de P2P; no equivale a la mediana externa |
| DolarApi Bolivia | tabla `quotes` y `data/p2p/quotes.csv` | Capturas desde la ejecución del recolector | Monitoreo prospectivo de Binance y oficial reportado por API | El endpoint entrega cotización actual, no historial anterior a la primera captura |

**Procedencia verificable.** `data/external/sources.json` guarda URL, fecha UTC de descarga, SHA-256, número de filas y primera/última fecha de los dos CSV externos. La licencia CC BY 4.0 y el método de la mediana se documentan en [paralelo.bo](https://paralelo.bo/metodologia). El PDF del BCB declara que el valor de Tether es un promedio ponderado de comercio P2P; las cifras BTC y ETH están en USD y no entran al cálculo de la brecha ([BCB, tabla histórica](https://www.bcb.gob.bo/webdocs/activos_virtuales/HISTORICO.pdf)).

### 3.2. Diccionario completo de las 18 variables mensuales seleccionadas

La clave `row` corresponde a la fila del layout Excel validado en `bcb_pipeline/parse.py`; las unidades se apoyan en la etiqueta y sección de `data/processed/catalog.csv`. **Presencia** es el número de meses no vacíos dentro de los 454 meses del archivo procesado, no una garantía de comparabilidad económica en todo el período.

| Clave | Fila | Concepto económico y unidad | Presencia | Uso efectivo |
|---|---:|---|---:|---|
| `base_monetaria` | 8 | Base monetaria, millones de Bs; stock monetario | 454 | Serie, ADF, SARIMA, validación, anomalías |
| `ipc` | 70 | IPC general, índice base 2016=100 | 454 | Descomposición, estacionalidad, ADF, SARIMA, inflación implícita |
| `inflacion_12m` | 73 | Variación interanual del IPC, % | 454 | Visualización de inflación; no se agrega al índice de estrés |
| `ahorro_mn` | 87 | Ahorro en MN del sistema financiero expresado en millones de USD en el cuadro | 454 | Base procesada y contexto; no entra en el índice |
| `ahorro_me` | 89 | Ahorro en ME, millones de USD | 454 | Base procesada y contexto |
| `bolivianizacion_ahorro` | 90 | Bolivianización del ahorro publicada por BCB, % | 454 | Base procesada y contexto; definición distinta de depósitos |
| `depositos_mn` | 92 | Depósitos en MN expresados en millones de USD según conversión del cuadro | 454 | Reconstrucción de MN en Bs y cambio neutral de bolivianización |
| `depositos_me` | 94 | Depósitos en ME, millones de USD | 454 | Índice neutral, ADF, SARIMA, simulación descriptiva de composición |
| `bolivianizacion_depositos` | 95 | Cifra publicada de bolivianización de depósitos, % | 454 | Se muestra como referencia de definición diferente; **no** alimenta el índice principal |
| `rib` | 141 | Reservas internacionales brutas, millones de USD | 454 | Índice, ADF, espectro, SARIMA, Monte Carlo |
| `rin` | 158 | Reservas internacionales netas, millones de USD | 454 | Contexto; no se duplica con RIB en el índice |
| `bolsin_sf` | 167 | Adjudicaciones de dólares en Bolsín al sistema financiero, millones de USD; flujo | 358 | Base procesada, contexto; no se modela en hipótesis |
| `ventas_directas_sf` | 169 | Adjudicaciones de dólares en ventas directas al sistema financiero, millones de USD; flujo | 166 | Base procesada, contexto |
| `compras_bcb_sf` | 171 | Compras de dólares del BCB al sistema financiero, millones de USD; flujo | 241 | Base procesada, contexto |
| `tc_fijo_bolsin` | 177 | Tipo de cambio de venta en Bolsín, Bs/USD | 447 | Referencia histórica; Bs 6,96 en tramo fijo del estudio |
| `tc_oficial` | 179 | Tipo de cambio oficial en el Excel, Bs/USD | 5 | Referencia mensual de jun-oct 2026 y comparación con CSV diario |
| `tc_referencial_venta` | 180 | Valor referencial de venta del dólar, Bs/USD | 6 | Referencia en dic-2025 a may-2026 |
| `tcr` | 182 | Índice de tipo de cambio real, dic-2022=100 | 322 | Variable contextual, sin modelo propio |

**Variables de identificación y datos auxiliares.** En las tablas largas, `date` es fecha, `freq` distingue A (anual), M (mensual), W (semanal) y D (diaria), `row` identifica la variable en el Excel, `value` es el número leído y `source_file` conserva el Excel de procedencia. `catalog.csv` guarda `row`, `section` y `label`; `vintage` registra qué Excel publicó una observación en `vintages.csv.gz`. `daily_key.csv` y `weekly_daily_long.csv` no se suman al número de 454 meses; son paneles de otra frecuencia.

### 3.3. Series P2P, oficiales y variables derivadas

| Nombre en archivo/código | Definición y unidad | Tratamiento |
|---|---|---|
| `median_bob_per_usd` → `paralelo` | Mediana P2P histórica, Bs por unidad de referencia USD/USDT | Fuente principal de H1/H3/H5; se conserva una sola definición por prueba |
| `Fecha`, `Valor` → `oficial` | Fecha y valor del CSV diario BCB, Bs/USD | Se usa desde 29-jun-2026; se excluye su tramo previo de 6,86 |
| `p2p_compra`, `p2p_venta` | Compra/venta Binance reportada por DolarApi, Bs/USD o Bs/USDT según la API | Captura propia; no se empalma con la mediana histórica |
| `of_compra`, `of_venta` | Compra/venta oficial reportada por DolarApi, Bs/USD | Registro propio; si existe, puede alimentar la referencia diaria auxiliar |
| `p2p_updated`, `of_updated`, `ts_utc` | Marcas de actualización de la fuente y de captura en UTC | Auditoría temporal; `ts_utc` se convierte a fecha de Bolivia al agregar por día |
| `usdt_compra`, `usdt_venta` | Precio Tether del PDF del BCB, Bs/USDT | Alternativa aislada cuando falta la mediana histórica; no se mezcla con ella |
| `btc_usd`, `eth_usd` | Precio BTC y ETH del PDF, USD por unidad | Solo preservación y revisión de extracción |
| `tc_efectivo` | Serie mensual jerárquica: oficial flexible, valor referencial, venta Bolsín | Denominador de brecha antes del TCO diario y descripción de regímenes |
| `tc_conversion` | Tipo usado para reconstruir MN en Bs: oficial cuando existe; Bolsín en otro caso | No usa el valor referencial de dic-2025 a may-2026 |
| `boliv_tc_vigente`, `boliv_tc_fijo` | Cocientes calculados de depósitos MN/ME a tipo vigente o constante, % | Explican efecto de valoración; fila 95 oficial se mantiene separada |
| `boliv_cambio_neutral` | Diferencia de bolivianización a un mismo tipo de cambio, puntos porcentuales en seis meses | Componente monetario del índice |
| `brecha_pct` | $100(P^{P2P}/E^{ref}-1)$, % | H1 y visualizaciones; nivel, no retorno |
| `daily_returns` | $\ln P_t-\ln P_{t-1}$, proporción por día calendario consecutivo | H3; se descartan diferencias que cruzan huecos |
| `lead_lag` | Retornos logarítmicos hábiles de P2P y oficial desde julio de 2026 | H5; excluye fines de semana y huecos largos |

## 4. Arquitectura del proyecto y metodología de datos

### 4.1. Obtención de Excel y cobertura temporal

`bcb_pipeline/download.py` consulta el [listado real del BCB](https://www.bcb.gob.bo/?q=estad-sticas-semanales), extrae los enlaces `.xlsx` del HTML, reconoce año y semana del nombre publicado y guarda copias locales como `Semanal_AAAA_SS.xlsx`. Los enlaces no se construyen por adivinación. El listado está paginado con `&page=N` y el código recorre desde lo más reciente. `--latest` obtiene una semana; `--since-year` reúne las semanas disponibles desde un año. Las descargas son **seriales** y se esperan al menos **1,5 s entre archivos**. Si el sitio deniega acceso, el procedimiento previsto es descargar el Excel manualmente; no se fuerza la fuente.

Cada Excel semanal contiene una historia **mensual extensa**, además de columnas semanales y diarias recientes. Por ello, `build.py` toma la historia mensual del archivo más reciente y concatena varios Excel para ampliar cobertura semanal/diaria. Para una misma fecha/frecuencia/fila publicada en más de un Excel, conserva la última versión ordenada por nombre de archivo. Con `--keep-vintages` guarda todas las publicaciones originales en `vintages.csv.gz`, lo que permite estudiar revisiones. Un riesgo residual es que la regla «última versión» depende del orden de nombres y debe revisarse si cambia el formato editorial del BCB.

### 4.2. Parseo y control de layout

`bcb_pipeline/parse.py` abre el Excel con `openpyxl` y valores calculados (`data_only=True`). Interpreta la fila 3 como cabecera mensual o «Semana n», la fila 4 como fecha semanal/diaria, y lee valores numéricos desde la columna E. Clasifica frecuencia, fecha, fila y fuente; omite celdas no numéricas y reconoce secciones y etiquetas. El catálogo final muestra qué significa cada fila. `KEY_VARIABLES` asocia 18 claves económicas con una fila y un patrón de etiqueta; `check-layout` informa cuando la etiqueta ya no coincide y exige revisar el mapeo antes de interpretar datos. Las expresiones de algunas filas son amplias (`ipc`, `inflacion_12m`); por ello la inspección del catálogo y la prueba de regresión son controles necesarios.

`bcb_pipeline/build.py` produce `monthly_long.csv` (historia larga mensual/anual), `weekly_daily_long.csv` (panel de alta frecuencia), `monthly_key.csv` (18 variables mensuales en columnas), `daily_key.csv` (variables recientes por frecuencia y fecha), `catalog.csv` y, cuando se solicita, `vintages.csv.gz`. Estas tablas son **derivados regenerables**. Los Excel de `data/raw/` se preservan tal como se descargaron y no se editan a mano.

### 4.3. PDF, recolector y series históricas externas

`bcb_pipeline/virtual_assets.py` extrae texto con `pdfplumber`, identifica filas `día/mes/año, Tether compra, Tether venta, BTC, ETH`, convierte coma decimal y punto de miles, elimina fechas duplicadas e inserta en SQLite. El importador se validó con el [PDF histórico completo de 2024](https://www.bcb.gob.bo/webdocs/activos_virtuales/HISTORICO.pdf), que contiene 15 fechas. **No se afirma** que el repositorio incluya una historia PDF continua de 2025-2026. El BCB también presenta [tablas de activos virtuales en su sitio](https://www.bcb.gob.bo/librerias/indicadores/virtuales/r_activos.php), pero integrar esas páginas constituye un trabajo distinto del importador PDF documentado aquí.

`bcb_pipeline/collector.py` consulta los endpoints `/binance` y `/oficial` de DolarApi, registra compra, venta y marcas de actualización, y almacena una captura en SQLite o CSV. `collect --loop` repite la captura; el servicio no aporta retrospectivamente días anteriores a la primera ejecución. El repositorio incluye una automatización horaria de GitHub Actions para mantener el CSV, cuya continuidad depende de la ejecución y disponibilidad de la API. Una cotización Binance no sustituye a la mediana entre plataformas ni al promedio ponderado del PDF.

`bcb_pipeline/historical.py` descarga los CSV originales de [paralelo.bo](https://paralelo.bo/api/v1/historical.csv) y del [BCB](https://www.bcb.gob.bo/bcb_tco_publico_evolutivo.php), verifica columnas, fechas ordenadas, duplicados, longitud mínima y rango numérico, y escribe `sources.json`. No completa valores faltantes con datos sintéticos. `stress_monitor/data.py` carga ambas fuentes y construye la brecha manteniendo la definición de P2P separada de las alternativas. El historial externo es una **fuente secundaria para el precio P2P** y el CSV del TCO es una publicación del BCB; la validez económica de la primera depende de su metodología declarada y cobertura efectiva.

### 4.4. Trazabilidad y reproducibilidad

La secuencia normal desde la raíz del repositorio es:

```bash
pip install -r requirements.txt
python -m bcb_pipeline download --latest
python -m bcb_pipeline download --since-year 2025
python -m bcb_pipeline build --keep-vintages
python -m bcb_pipeline fetch-history
python -m stress_monitor.report
python notebooks/build_notebooks.py
python -m pytest -q
streamlit run app/streamlit_app.py
```

La primera descarga basta para actualizar la historia mensual; la segunda ayuda a ampliar el panel semanal/diario. Para reproducir **exactamente** los resultados numéricos de este informe conviene utilizar el estado versionado del 13 de noviembre y su `sources.json`, pues nuevas descargas pueden añadir observaciones o revisiones. `reports/INFORME.md` y `reports/results.json` son productos automáticos; el presente documento académico es un texto explicativo independiente y puede requerir actualización editorial cuando cambie el corte.

## 5. Marco estadístico: capítulos 1 y 2 del curso

### 5.1. Series como procesos estocásticos

Una serie económica observada $x_1,\ldots,x_T$ se interpreta como una realización de variables aleatorias $\{X_t\}$ indexadas en el tiempo. Esta lectura importa porque los valores consecutivos suelen depender entre sí: una reserva alta este mes hace más probable una reserva alta el siguiente, aun sin nueva presión. No es válido tratar los meses como observaciones independientes de una encuesta transversal. El proyecto calcula momentos de variaciones de RIB y usa la **función de autocorrelación (ACF)** y la **autocorrelación parcial (PACF)** para estudiar dependencia a distintos rezagos.

La media $E[X_t]$, la varianza (Var(X_t)) y la autocovarianza $Cov(X_t,X_{t-k})$ son las cantidades básicas. En una serie débilmente estacionaria, la media y la varianza no cambian con (t), y la autocovarianza depende del rezago (k), no del mes calendario. Esta propiedad facilita interpretar un AR(1) con parámetros constantes y construir pronósticos. Las series en nivel como IPC o reservas pueden contener tendencias y quiebres; trabajar con logaritmos y diferencias reduce algunos problemas, pero no elimina automáticamente un cambio estructural.

El proyecto usa las transformaciones:

$$
y_t=\ln X_t,\quad \Delta y_t=y_t-y_{t-1},\quad
100\Delta y_t\approx \text{variación porcentual mensual de }X_t.
$$

La aproximación porcentual es buena para cambios pequeños; una variación interanual usa $\Delta_{12}y_t=y_t-y_{t-12}$. Una serie debe ser positiva antes de aplicar logaritmo. `stress_monitor/stationarity.py` calcula momentos, ACF/PACF y pruebas ADF; el notebook `cap1_2_estacionariedad.ipynb` presenta estas operaciones sobre RIB, IPC, depósitos ME y base monetaria.

### 5.2. Prueba de Dickey-Fuller aumentada

La ADF contrasta una **raíz unitaria** contra una alternativa sin raíz unitaria bajo una especificación de rezagos y términos deterministas. En el proyecto se usa constante, selección de rezagos por AIC y nivel de significancia del 5 %, a través de `statsmodels` ([Dickey y Fuller, 1979](https://doi.org/10.1080/01621459.1979.10482531); [documentación de ADF](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.adfuller.html)). La hipótesis nula no se «acepta» cuando $p>0,05$: sencillamente no se rechaza con esa muestra y especificación.

Los resultados almacenados para datos desde 1995 muestran que los logniveles de RIB $p=0,508$, IPC $p=0,993$, depósitos ME $p=0,055$ y base monetaria $p=0,882$ no rechazan la raíz unitaria al 5 %. Sus logdiferencias sí la rechazan en la especificación aplicada: RIB $p=0,046$, IPC $p<0,001$, depósitos ME $p<0,001$ y base monetaria $p=0,002$. Esto **orienta** la diferenciación de SARIMA, pero la ADF puede tener poca potencia ante quiebres de nivel y no demuestra estabilidad de todos los parámetros. El resultado de RIB en diferencias está cerca del umbral y exige prudencia.

### 5.3. ACF, PACF y dependencia temporal

La ACF estima la asociación lineal entre $X_t$ y $X_{t-k}$; la PACF aproxima la asociación adicional del rezago (k) una vez considerados los intermedios. Son herramientas exploratorias para reconocer persistencia, ciclos o estacionalidad, y para identificar candidatos AR y MA. Las bandas $\pm1,96/\sqrt{T}$ que muestra el módulo son aproximaciones bajo condiciones de ruido blanco; múltiples rezagos examinados pueden producir excedencias por azar. El informe generado contiene la [figura ACF/PACF de cambios en RIB](figures/fig_acf_rib.png).

## 6. Capítulo 3: índice de estrés y cadenas de Markov

### 6.1. Construcción y lectura del índice

`stress_monitor/markov.py` define dos componentes mensuales con signo orientado a que un valor mayor implique más tensión:

$$
Z^{RIB}_t=-z\!\left(100[\ln RIB_t-\ln RIB_{t-12}]\right),\qquad
Z^{B}_t=-z\!\left(\Delta_6B_t^{neutral}\right),\qquad
I_t=\frac{Z^{RIB}_t+Z^{B}_t}{2}.
$$

Aquí $z(x)=(x-\bar x)/s_x$ se calcula con la **muestra completa disponible**. Una pérdida interanual de reservas y una caída de bolivianización neutralizada suben el índice. La construcción toma el promedio solo cuando existen los dos componentes. El índice no incluye la brecha reciente porque introducirla a partir de 2024 cambiaría la regla de medición de $I_t$ en mitad de su historia. Tampoco es el índice del FMI de presión de mercado: comparte la intuición de usar señales de tensión, pero no su fórmula ni su objetivo de inferencia.

La estandarización con toda la muestra implica que los estados históricos podrían recalcularse cuando ingresan nuevos meses. Esto es aceptable para **descripción retrospectiva**, pero no para presentar las probabilidades como un sistema predictivo probado en tiempo real. En una versión operacional futura convendría fijar media, desviación y umbrales con una muestra de entrenamiento anterior a cada evaluación.

### 6.2. Estados, transición y permanencia

`classify` asigna «Estable» bajo el percentil 60 de $I_t$, «Tensión» entre los percentiles 60 y 85, y «Crisis» desde el percentil 85. En esta muestra los cortes son aproximadamente **0,32** y **0,72** unidades estandarizadas. «Crisis» significa **cola superior del índice construido**, no una calificación institucional. El tablero permite cambiar los cuantiles; el informe compara cuatro pares de umbrales para mostrar sensibilidad.

Una cadena de Markov de primer orden postula $P(S_{t+1}=j\mid S_t=i,S_{t-1},\ldots)=P(S_{t+1}=j\mid S_t=i)=p_{ij}$. Se cuentan transiciones mensuales y se estiman $p_{ij}=n_{ij}/\sum_j n_{ij}$. La matriz obtenida es:

| Estado actual → siguiente | Estable | Tensión | Crisis |
|---|---:|---:|---:|
| Estable | 0,932 | 0,064 | 0,004 |
| Tensión | 0,173 | 0,709 | 0,118 |
| Crisis | 0,000 | 0,224 | 0,776 |

La **probabilidad de permanencia** es el elemento diagonal. Si la matriz fuese estable y el modelo de primer orden fuera una descripción adecuada, la duración esperada de una visita al estado (i) sería $1/(1-p_{ii})$: **14,7 meses Estable**, **3,4 Tensión** y **4,5 Crisis**. La distribución estacionaria satisface $\pi P=\pi$ y suma uno; aquí es **61,7 % Estable**, **24,4 % Tensión**, **13,9 % Crisis**. Es una propiedad de la matriz estimada y **no** una frecuencia garantizada de crisis futuras.

En octubre de 2026 el índice clasifica el mes como «Estable». La matriz estima, condicional a ese estado y a mantenerse sus transiciones, una probabilidad a un mes de **93,2 % Estable**, **6,4 % Tensión** y **0,4 % Crisis**. A seis meses son **75,3 %, 18,3 % y 6,4 %**. Estas son extrapolaciones matemáticas de $P^h$, no predicciones validadas ante un nuevo régimen económico.

### 6.3. Contrastes, episodios y limitación económica

La prueba de independencia sobre la tabla de transiciones da $\chi^2=465,48$, $p\approx1,96\times10^{-99}$: hay fuerte dependencia entre estados consecutivos. El contraste de **primer orden frente a segundo orden** produce $LR=28,81$, $p=0,00034$; por tanto, se rechaza la suficiencia estadística del modelo de primer orden en esta muestra. Es razonable usarlo como **resumen parsimonioso de persistencia**, con ese límite explícito. Las ventanas móviles de 12 y seis meses que generan el índice también inducen solapamiento y persistencia mecánica.

La validación narrativa compara episodios definidos antes de mirar el estado: bonanza 2006-2013, caída de reservas 2014-2019, pandemia 2020, escasez de dólares 2023-2025, transición referencial y régimen flexible. El índice marca «Crisis» en **67 %** de los meses de 2020 y **46 %** de los meses del episodio 2023-2025, pero marca **«Estable» en todos los meses** de diciembre de 2025 a mayo de 2026 y de junio a octubre de 2026. Este contraste no debe ocultarse: muestra que reservas y composición monetaria no contienen toda la información que aporta el mercado P2P. La [figura de estados](figures/fig_markov_estados.png) permite revisar esta lectura.

## 7. Capítulo 4: descomposición y suavizamiento exponencial

La descomposición clásica separa el IPC en tendencia $T_t$, patrón estacional $S_t$ y residuo $e_t$. En forma multiplicativa, $IPC_t=T_tS_te_t$; en logaritmos se vuelve una suma. El período considerado es de 12 meses. El cálculo de **fuerza estacional** usa una versión aditiva en logaritmos, $F_s=\max\{0,1-\mathrm{Var}(e_t)/\mathrm{Var}(S_t+e_t)\}$. Para el IPC de la muestra se obtiene **0,042**, valor bajo frente al criterio operativo **0,64** empleado en el código para activar diferencia estacional $D=1$. El corte 0,64 sigue una regla de selección descrita por [Hyndman y Athanasopoulos](https://otexts.com/fpptr/stationarity.html); su adopción sigue siendo una elección de modelado, no una ley económica. La [figura de descomposición](figures/fig_descomposicion_ipc.png) ilustra tendencia, estacionalidad y residuo.

Holt-Winters combina nivel, tendencia y estacionalidad mediante suavizamiento exponencial; el proyecto usa tendencia amortiguada y componente estacional aditivo sobre logaritmos. Se incorpora como **referencia de pronóstico**, no como modelo estructural de inflación. La comparación con SARIMA e ingenuo permite determinar si mayor complejidad mejora efectivamente el error reciente.

## 8. Capítulo 5: AR(1), brecha, espectro y volatilidad

### 8.1. AR(1) y vida media de la brecha (H1)

El modelo ajustado desde el inicio del régimen flexible es:

$$
G_t=c+\phi G_{t-1}+\varepsilon_t.
$$

Si $0<\phi<1$, una desviación respecto a la media condicional se reduce aproximadamente en proporción $\phi$ por paso. La media de largo plazo del modelo es $c/(1-\phi)$; la **vida media** en la frecuencia de observación es $\ln(0,5)/\ln(\phi)$. El programa rechaza series con huecos mayores a un día para no llamar «diario» al salto entre años. Con **138 fechas consecutivas** desde el 29 de junio de 2026, $\hat\phi=0,842$, error estándar (0,046), y vida media **4,02 días calendario**; la ADF de la brecha da $p=8,86\times10^{-5}$. Así, H1 es **compatible** con una brecha que vuelve hacia su media en esta ventana y con una vida media menor a 30 días.

Esta conclusión es local: el régimen nuevo tiene pocos meses, el denominador es TCO de compra, el numerador es un punto medio P2P, y el AR(1) no incorpora directamente cambios de metodología, fines de semana ni anuncios de política. La «media de largo plazo» estimada de **0,635 %** es un parámetro del ajuste, no un equilibrio económico observado o garantizado. Una ADF significativa tampoco prueba que la relación conserve el mismo $\phi$ en años futuros.

### 8.2. Análisis espectral de reservas

El periodograma distribuye la variación de $\Delta\ln RIB_t$ entre frecuencias $f$ (ciclos por mes); un período aproximado en meses es $1/f$. `stress_monitor/stationarity.py` elimina la frecuencia cero y descarta períodos mayores a 60 meses para atenuar la confusión entre oscilación muy lenta y tendencia. Aplica una ventana Hann y destaca máximos separados en frecuencia. Entre los picos aparecen períodos cercanos a **2,8** y **11,9 meses**. Un pico cercano a 12 meses podría ser compatible con una componente anual, pero **un periodograma solo no demuestra causalidad ni estabilidad de un ciclo**. Se muestra en la [figura espectral](figures/fig_espectro_rib.png).

### 8.3. Cambio de volatilidad P2P (H3)

La volatilidad se aproxima por la desviación estándar de retornos logarítmicos diarios $r_t=\ln P_t-\ln P_{t-1}$. Para evitar que una revisión metodológica del proveedor se interprete como cambio económico, H3 se calcula solo entre el **4 de mayo y el 3 de septiembre de 2026**. Este período sigue al lanzamiento del método de paralelo.bo y precede el cambio registrado el 4 de septiembre ([historial de metodología](https://paralelo.bo/metodologia)). El corte entre regímenes es el **29 de junio de 2026**; se comparan **56 retornos anteriores** y **67 posteriores**.

La desviación estándar pasa de **0,470 % diario** a **1,123 % diario**, una razón de **2,392**. La prueba de Levene centrada en la mediana, también llamada variante Brown-Forsythe, contrasta igualdad de dispersión y arroja $p=3,82\times10^{-5}$. Al excluir los primeros siete días del período flexible, la razón es **2,52** y $p=1,71\times10^{-5}$; el resultado no depende solo de esa primera semana. Es evidencia de **diferencia de variabilidad dentro de la ventana elegida**, no demostración causal de que la reforma produjo el cambio: los retornos pueden tener autocorrelación, la muestra es corta y no se controlan otras noticias. La tabla de variaciones mensuales del tipo de referencia en el informe automático es **descriptiva** y no sustituye esta prueba formal P2P.

### 8.4. Correlación cruzada y Granger (H5)

La correlación cruzada calculada es $\rho(k)=Corr(r^{P2P}_t,r^{TCO}_{t+k})$: si $k>0$, el retorno P2P de hoy se compara con el TCO posterior. El código alinea ambos niveles desde julio de 2026, toma solo días hábiles, calcula retornos logarítmicos, descarta huecos superiores a cuatro días y exige al menos **90 retornos comunes** y **20 cambios no nulos del TCO**. Hay **97 retornos hábiles** y la mayor correlación absoluta entre rezagos distintos de cero ocurre en $k=+1$, con **0,658**.

La prueba de precedencia de Granger compara si rezagos de una variable reducen el error de una regresión de la otra, condicionando también a los rezagos propios. Para **un rezago**, P2P → TCO arroja $p=9,21\times10^{-10}$ y TCO → P2P $p=0,293$ en la especificación aplicada ([Granger, 1969](https://doi.org/10.2307/1912791); [implementación de statsmodels](https://www.statsmodels.org/v0.14.4/generated/statsmodels.tsa.stattools.grangercausalitytests.html)). Se observa, por tanto, **adelanto predictivo a un día hábil**, compatible con H5 en esta muestra. La prueba se inspecciona hasta cinco rezagos y no incorpora ajuste por búsquedas múltiples; además, el horario y la convención de fecha del TCO pueden generar un adelanto aparente. No hay identificación causal ni evidencia suficiente para afirmar que operaciones P2P «determinan» el TCO.

## 9. Capítulo 6: Box-Jenkins y pronóstico SARIMA

### 9.1. Teoría y selección del modelo

Un SARIMA\((p,d,q)\times(P,D,Q)_{12}\) combina autorregresión, diferencias, medias móviles y efectos anuales sobre una serie mensual. $p,q$ controlan dinámica corta; $d$ elimina una raíz unitaria no estacional; $P,Q,D$ hacen lo análogo a 12 meses. El proyecto ajusta el **logaritmo de la serie** desde enero de 2005. `choose_d` usa ADF con $d\le1$; `choose_D` aplica el criterio de fuerza estacional; `select_sarima` explora $p,q\in\{0,1,2\}$ y $P,Q\in\{0,1\}$, seleccionando el menor AIC entre ajustes con AIC finito. El código no exige verificar convergencia antes de comparar AIC; los ajustes con advertencia deben revisarse. La estimación utiliza `SARIMAX` de statsmodels mediante máxima verosimilitud y filtro de Kalman ([documentación SARIMAX](https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.sarimax.SARIMAX.html)).

La selección por AIC equilibra ajuste y número de parámetros dentro de la malla, pero **no garantiza** el mejor pronóstico fuera de muestra. Los pronósticos se obtienen en logaritmos y se exponencian junto con sus intervalos del 95 %. Exponenciar directamente la media pronosticada en log produce una mediana aproximada en la escala original bajo lognormalidad; por ello la columna llamada `media` en la salida **no debe interpretarse como media aritmética insesgada** sin una corrección de transformación. Este detalle importa si se comparan expectativas en niveles.

| Variable | Orden no estacional | Orden estacional | Interpretación de uso |
|---|---|---|---|
| RIB | (2,1,2) | (0,0,0,12) | Pronóstico de reservas; la diferencia aborda tendencia |
| IPC | (2,1,1) | (0,0,0,12) | Pronóstico del nivel del índice e inflación implícita |
| Depósitos ME | (1,1,1) | (0,0,0,12) | Pronóstico de depósitos en USD |
| Base monetaria | (1,0,0) | (1,0,1,12) | Dinámica mensual con componentes estacionales AR/MA |

### 9.2. Diagnóstico residual y anomalías

`diagnostics` descarta los primeros **24 residuos** para reducir efectos de inicialización. La prueba **Ljung-Box** a 12 y 24 rezagos contrasta ausencia conjunta de autocorrelación residual; **Jarque-Bera** contrasta normalidad mediante asimetría y curtosis ([documentación de Ljung-Box](https://www.statsmodels.org/dev/generated/statsmodels.stats.diagnostic.acorr_ljungbox.html)). Resultados:

| Serie | Ljung-Box p(12) | p(24) | Jarque-Bera p | Lectura |
|---|---:|---:|---:|---|
| RIB | <0,001 | 0,001 | <0,001 | Autocorrelación y no normalidad residual |
| IPC | 0,040 | 0,001 | <0,001 | Autocorrelación y no normalidad |
| Depósitos ME | 0,989 | 0,993 | <0,001 | Sin autocorrelación detectada en esos rezagos; no normalidad |
| Base monetaria | 0,099 | 0,008 | 0,001 | Autocorrelación a 24 rezagos y no normalidad |

Estos diagnósticos impiden afirmar que los cuatro modelos están bien especificados o que los intervalos gaussianos tienen cobertura nominal. El módulo de alertas define $z_t=(e_t-\bar e)/s_e$ y marca $|z_t|>2,5$, sobre residuos posteriores al descarte inicial. Una alerta indica **observación inusual respecto al modelo**, no fraude, crisis ni error de los datos. La [figura de anomalías](figures/fig_anomalias.png) conserva el contexto de cada serie.

### 9.3. Validación temporal y H4

La comparación utiliza 24 orígenes recientes con ventana de entrenamiento creciente y horizontes de **1, 3 y 6 meses**. En cada origen se reestima el modelo elegido, un pronóstico ingenuo que repite el último nivel y Holt-Winters. El **MAPE** promedia $100|\hat y-y|/|y|$; el **RMSE** penaliza más errores grandes; la cobertura del intervalo SARIMA registra la proporción de reales entre sus límites del 95 %. Son medidas de error de pronóstico, no de causalidad ni de calidad de política monetaria.

| Serie | Horizonte | SARIMA MAPE % | Ingenuo % | Holt-Winters % | Cobertura IC95 SARIMA |
|---|---:|---:|---:|---:|---:|
| RIB | 1 | 7,67 | **6,94** | 7,70 | 0,54 |
| RIB | 3 | 11,54 | **10,61** | 11,34 | 0,67 |
| RIB | 6 | 20,03 | **16,62** | 17,41 | 0,62 |
| IPC | 1 | 0,92 | 1,26 | **0,86** | 0,62 |
| IPC | 3 | 2,92 | 3,56 | **2,50** | 0,38 |
| IPC | 6 | 5,78 | 6,61 | **5,13** | 0,25 |
| Depósitos ME | 1 | **0,86** | 1,11 | 0,95 | 0,96 |
| Depósitos ME | 3 | **1,77** | 2,58 | 1,85 | 1,00 |
| Depósitos ME | 6 | 2,62 | 4,00 | **2,46** | 1,00 |
| Base monetaria | 1 | **1,45** | 2,00 | 1,82 | 1,00 |
| Base monetaria | 3 | **3,19** | 4,35 | 3,79 | 1,00 |
| Base monetaria | 6 | **4,89** | 7,28 | 5,63 | 1,00 |

H4 («SARIMA supera al ingenuo») tiene resultado **mixto**: gana al ingenuo en los tres horizontes de IPC, depósitos ME y base monetaria, pero pierde en los tres de RIB. Además, Holt-Winters vence a SARIMA para IPC y para depósitos ME a seis meses. La cobertura de RIB e IPC queda muy por debajo del 95 % nominal. **Limitación de diseño:** la especificación SARIMA se seleccionó una vez usando la serie completa y luego se reutilizó en la validación retrospectiva. Aunque los coeficientes se reestiman en cada origen, la elección previa de órdenes pudo aprovechar información posterior al origen; por ello la comparación no es una validación estrictamente anidada. Una evaluación futura debe repetir la selección dentro de cada ventana de entrenamiento o fijar una especificación anterior al período de prueba. La [figura de pronósticos](figures/fig_pronosticos.png) es ilustrativa de los ajustes al corte, no de esa validación más estricta.

## 10. Capítulo 7: Monte Carlo y escenarios de riesgo

### 10.1. Movimiento browniano geométrico

`stress_monitor/simulation.py` utiliza un movimiento browniano geométrico (GBM) como **modelo de escenarios positivos**:

$$
S_{t+h}=S_t\exp\left[\left(\mu-\frac{\sigma^2}{2}\right)h+\sigma W_h\right],
$$

donde $W_h$ representa una suma de innovaciones normales independientes. En la implementación discreta, `gbm_paths` toma innovaciones normales con generador y semilla fijos, suma incrementos logarítmicos y produce trayectorias estrictamente positivas. `estimate_gbm` calcula media y desviación estándar de los últimos **36 logretornos mensuales** de RIB. **Detalle de parametrización:** la media calculada es una media logarítmica, pero la función simuladora le vuelve a restar $\sigma^2/2$, corrección habitual si $\mu$ fuese deriva aritmética. El crecimiento logarítmico simulado queda algo por debajo de la media logarítmica estimada; las probabilidades reportadas describen esa implementación exacta. La normalidad, independencia y estabilidad de $\mu,\sigma$ son supuestos de simulación, no hechos demostrados para Bolivia.

### 10.2. Escenario de reservas

Con RIB inicial de **3.964,9 millones de USD**, media mensual de logretornos **2,43 %**, desviación estándar **9,08 %**, **10.000 trayectorias**, horizonte de seis meses y umbral arbitrario de **3.500 millones de USD**, el modelo estima **13,67 %** de trayectorias que terminan bajo el umbral y **26,76 %** que lo cruzan al menos una vez durante los seis meses. El segundo evento es más amplio que el primero: una trayectoria puede caer y recuperarse antes del final. El valor de 3.500 no es una regla oficial de suficiencia de reservas; es un parámetro de escenario que el tablero permite modificar. El usuario también puede variar horizonte y multiplicador de volatilidad. La [figura Monte Carlo](figures/fig_montecarlo_rib.png) muestra bandas percentilares, no intervalos de confianza de una estimación causal.

### 10.3. Escenario de costo cambiario

El simulador convierte un monto de USD a Bs con $C_T=USD\cdot E_T$. Por defecto estima la dispersión diaria del TCO desde agosto de 2026, excluyendo el salto inicial de transición; también ofrece la serie propia P2P si el recolector reúne suficientes días o una volatilidad manual. Para observaciones con intervalos desiguales, `fx_params` usa $\hat\sigma^2=\sum r_t^2/\sum\Delta t$ y $\hat\mu=\sum r_t/\sum\Delta t$. En la **pantalla**, la deriva se fija mediante un control del usuario (predeterminado cero); el informe automático usa deriva cero para su ejemplo, aunque `fx_params` reporte una media histórica diferente.

Con la fotografía del 13 de noviembre, el ejemplo de **USD 10.000**, tipo inicial **Bs 11,67/USD**, horizonte **90 días**, volatilidad diaria estimada **1,73 %** a partir de **104 variaciones** y **20.000 simulaciones** produce costo actual **Bs 116.700**, percentil 5 **Bs 87.784**, mediana **Bs 114.972** y percentil 95 **Bs 150.921**. Estas cifras cambian con los supuestos y con la semilla de simulación. El percentil 95 es un **cuantil del modelo**, no una pérdida máxima posible ni una recomendación para contratar una deuda. Un GBM con volatilidad constante puede subestimar cambios bruscos y colas pesadas; el informe automático documenta precisamente residuos no normales en varias series.

## 11. Hipótesis de investigación: definición, prueba y conclusión

| Hipótesis | Operacionalización y muestra | Resultado guardado al 13-nov-2026 | Conclusión admisible |
|---|---|---|---|
| **H1.** La brecha oficial–P2P revierte hacia una media con vida media menor a 30 días | AR(1) del nivel de la brecha post-29-jun-2026, 138 fechas; ADF con constante | $\phi=0,842$, vida media **4,02 días**, ADF $p=8,86\times10^{-5}$ | Compatible con H1 en esta ventana; no garantiza reversión estable futura |
| **H2.** Los estados del índice monetario son persistentes y pueden resumirse con Markov | Índice mensual, matriz de tres estados, independencia y prueba de orden | $p_{EE}=0,932$, $p_{CC}=0,776$; independencia $p\approx2\times10^{-99}$; primer orden frente a segundo $p=0,00034$ | Persistencia clara; cadena de primer orden **solo aproximación**, pues su suficiencia se rechaza |
| **H3.** La volatilidad P2P cambia entre regímenes | Retornos diarios de misma serie y metodología, 4-may a 3-sep; 56 antes/67 después | $s_{pre}=0,470\%$, $s_{post}=1,123\%$, razón **2,39**, Levene-mediana $p=3,82\times10^{-5}$ | Diferencia estadística de dispersión; no atribución causal a la reforma |
| **H4.** SARIMA mejora el pronóstico ingenuo | MAPE en 24 orígenes, horizontes 1/3/6 meses, cuatro series | Mejora en IPC, depósitos ME y base monetaria; empeora en RIB; Holt-Winters gana al IPC | Resultado **mixto**; selección de órdenes previa impide validación estrictamente anidada |
| **H5.** El P2P antecede estadísticamente al TCO | 97 retornos hábiles desde julio; correlación cruzada y Granger de un rezago | Máximo $k=+1$, $\rho=0,658$; P2P→TCO $p=9,21\times10^{-10}$, reverso $p=0,293$ | Compatible con adelanto predictivo de un día; **sin inferencia causal** |

Las pruebas H1, H3 y H5 emplean datos P2P **observados por una fuente pública**, no datos DEMO ni una curva sintética basada en noticias. Sus estimandos son distintos: H1 usa el **nivel de una brecha**, H3 la **dispersión de retornos P2P**, y H5 la **asociación entre dos retornos hábiles**. Sus valores $p$ tampoco son la probabilidad de que la hipótesis sea verdadera: cuantifican la compatibilidad de los datos con una hipótesis nula bajo los supuestos de cada prueba.

## 12. Tablero Streamlit: explicación de las siete pantallas

1. **Semáforo del sistema.** Muestra índice monetario, estado del último mes, dos componentes estandarizados, matriz (P), distribución estacionaria, permanencia media y probabilidades a 1, 3 y 6 meses. Permite modificar percentiles de Tensión y Crisis y presenta validación por episodios y robustez a umbrales. La brecha P2P se analiza en otra pantalla para preservar la regla del índice desde 1989.
2. **Brecha cambiaria.** Compara fijo del Bolsín, valor referencial y oficial flexible; grafica P2P y referencia BCB; ofrece el AR(1) de H1, ADF, banda del modelo, correlación cruzada, Granger y la comparación de volatilidad H3. Indica la fuente de la mediana y la advertencia de que un anuncio P2P no es una transacción. El interruptor **DEMO** permanece explícitamente identificado y no es parte de resultados reales ni del informe.
3. **Reservas y depósitos.** Permite elegir RIB, depósitos ME, base monetaria o IPC; muestra pronóstico SARIMA e intervalo, diagnóstico Ljung-Box/Jarque-Bera y tabla de validación. Para RIB abre el escenario Monte Carlo y sus umbrales; para depósitos ME muestra la divergencia entre bolivianización calculada a tipo vigente y a tipo constante. El aviso académico y de no asesoría está presente.
4. **Inflación.** Grafica IPC, inflación a 12 meses, componentes de la descomposición clásica y fuerza estacional; muestra el pronóstico del IPC y su inflación interanual implícita. No afirma que inflación y tipo de cambio tengan una relación causal estimada por el tablero.
5. **Simulador de riesgo cambiario.** Recibe monto USD, plazo, tipo inicial, deriva y fuente de volatilidad; dibuja 20.000 costos terminales y cuantiles 5/50/95. El usuario debe leerlo como **escenario sensible al régimen y a los supuestos**, no como precio futuro garantizado. Incluye el aviso «no es asesoría financiera».
6. **Alertas.** Informa si la última observación mensual es antigua, si el estado del índice cambió y si alguna serie tiene residuo SARIMA estandarizado con |z|>2,5 en los últimos 24 meses. Una alerta es señal para revisar datos/modelo; no diagnostica una crisis.
7. **Metodología.** Relaciona cada capítulo del curso con su implementación, enumera fuentes y recuerda limitaciones. Conduce al informe generado para cifras y al presente documento para justificación académica completa.

`app/streamlit_app.py` usa caché para lecturas y ajustes costosos. El tablero lee los CSV locales y `reports/results.json`; su información será tan reciente como la última actualización de esos archivos. El script de generación de notebooks construye seis cuadernos ejecutados por capítulo; el capítulo 5 contiene H1, H3 y H5 con la serie externa real. `stress_monitor/report.py` genera resultados y figuras de forma programática para evitar copiar cifras manualmente. En el corte documentado, **38 pruebas automatizadas** pasaron; eso verifica comportamiento del software y casos de regresión, no valida por sí solo cada supuesto económico o estadístico.

## 13. Discusión crítica y límites de validez

### 13.1. Medición y comparabilidad

**Distinto instrumento y lado del precio.** La mediana P2P es un punto medio de anuncios USDT/BOB, mientras el TCO es una referencia oficial de compra de USD en el sistema financiero. La brecha incorpora más que escasez de divisas; no representa el costo neto de cambiar un USD bancario por un USDT ni una ganancia de arbitraje. En una extensión, habría que comparar precios ejecutables del mismo lado, volumen mínimo, costos y horarios.

**Cambios de fuente.** El CSV P2P contiene reconstrucción anterior al lanzamiento del proveedor del 3 de mayo de 2026; su método cambió el 4 de septiembre de 2026 ([bitácora de paralelo.bo](https://paralelo.bo/metodologia)). H3 limita deliberadamente la muestra para evitar ese cambio; H1 y H5 abarcan la modificación de septiembre y podrían ser sensibles a ella. El PDF BCB de 2024, DolarApi y la mediana no se empalman como si fueran una misma serie.

**Calendario y publicación.** Los fines de semana y feriados no equivalen a días de transacción bancaria, aunque la fuente pueda mostrar un valor vigente. El TCO tiene fecha de corte y fecha de vigencia. H5 usa días hábiles y rechaza huecos largos, pero una auditoría de horarios intradía y fecha de operación sería necesaria antes de interpretar el rezago como descubrimiento de precios.

**Revisiones del BCB.** Los Excel pueden republicar cifras pasadas. El archivo de `vintages` permite rastrear revisiones; los resultados de este informe usan la versión mensual del Excel más reciente disponible en el corte. Datos preliminares y revisiones pueden modificar tanto modelos como conclusiones cuantitativas. La fuente del listado de Excel es la [página de Estadísticas Semanales del BCB](https://www.bcb.gob.bo/?q=estad-sticas-semanales).

### 13.2. Inferencia estadística y capacidad predictiva

**Régimen nuevo y muestra corta.** H1 dispone de 138 días calendario y H5 de 97 retornos hábiles. Son suficientes para estimar los contrastes programados, pero insuficientes para inferir estabilidad de varios años o respuesta ante nuevas reformas. La prueba ADF es sensible al tipo de cambio estructural y a la especificación de tendencia/constante.

**Dependencia, heterocedasticidad y búsqueda de rezagos.** Levene presupone condiciones que los retornos financieros pueden incumplir por autocorrelación y agrupamiento de volatilidad; una versión con remuestreo en bloques o modelo de volatilidad condicional sería una comprobación útil. Para H5 se inspeccionan varios rezagos y se selecciona el de mayor correlación, lo que eleva el riesgo de encontrar extremos por búsqueda. Los valores $p$ de Granger dependen del orden elegido, datos faltantes, horarios y variables omitidas. No deben traducirse a «el paralelo causa el oficial».

**Modelo de Markov aproximado.** La propia prueba de orden 1 rechaza la hipótesis de que el último estado resuma toda la historia relevante. La discretización por percentiles obliga aproximadamente a que 15 % de meses queden en la etiqueta superior con la muestra usada; **la frecuencia de «Crisis» no es una tasa de crisis económicas objetivas**. La asignación de episodios es descriptiva y no una validación externa independiente de todos los componentes.

**Pronóstico y simulación.** Varias series tienen residuos SARIMA autocorrelacionados o no normales, y la cobertura empírica de IPC/RIB es baja. El selector puede admitir ajustes con AIC finito aun si advierten no convergencia. La especificación seleccionada con datos completos introduce información futura en la evaluación retrospectiva de pronósticos. GBM presupone innovaciones normales, parámetros constantes y ausencia de saltos; además, la implementación resta $\sigma^2/2$ a una media ya estimada en logretornos. Su probabilidad de cruzar un umbral depende del umbral elegido, horizonte, volatilidad y esta convención de deriva. Las simulaciones no incluyen reacciones de política económica.

### 13.3. Qué mejora sería metodológicamente prioritario

1. **Congelar convenciones de precio y reloj.** Identificar fecha de transacción, corte y vigencia del TCO; usar P2P del mismo lado y horario, con spread, liquidez y comisiones documentadas.
2. **Evaluar H1/H5 por subperíodos y método.** Repetir estimaciones antes y después del 4-sep-2026 cuando haya longitud suficiente; contrastar sensibilidad a fines de semana y feriados. No usar una submuestra demasiado corta como prueba concluyente.
3. **Anidar la selección de SARIMA.** Elegir órdenes solo dentro de cada entrenamiento, evaluar en un período realmente apartado, y comparar cobertura además de MAPE/RMSE.
4. **Hacer sensibilidad inferencial.** Remuestreo en bloques o errores robustos para diferencias de volatilidad; corrección por múltiples rezagos en H5; eventual GARCH como extensión **opcional**, no requisito ya implementado.
5. **Auditar revisiones y definiciones monetarias.** Estudiar `vintages` y documentar la definición oficial de la fila 95 para explicar, sin especular, su diferencia con las filas 92/94.
6. **Separar presentación y actualización.** Si se regeneran fuentes antes de la entrega, volver a correr pipeline, informe, notebooks y pruebas, y consignar un nuevo corte. Las cifras de este texto están fijadas al 13-nov-2026.

## 14. Conclusiones

El monitor convierte datos heterogéneos en una secuencia auditable de observaciones, transformaciones, modelos y pantallas. Su hallazgo económico más sólido es **contable**: medir depósitos MN en USD con un tipo de cambio mayor puede hacer caer la bolivianización calculada al tipo vigente sin que suban los depósitos en USD; por eso el índice emplea un cambio de composición a valoración homogénea. El semáforo resume reservas y depósitos, pero su clasificación «Estable» durante la transición muestra que es una señal **parcial** y que la brecha P2P reciente aporta información distinta.

En los datos disponibles, H1 encuentra una brecha con vida media estimada cercana a cuatro días, H3 detecta mayor dispersión diaria después del corte de régimen dentro de una ventana metodológicamente comparable, y H5 observa precedencia predictiva de un día hábil. H2 confirma persistencia, pero rechaza la suficiencia de una cadena de primer orden; H4 es mixta y exige validación estrictamente temporal para conclusiones fuertes. Por tanto, el resultado final es un **instrumento descriptivo y docente con hipótesis contrastadas**, no una predicción segura ni una explicación causal cerrada del mercado cambiario boliviano.

## Referencias y materiales de consulta

### Fuentes económicas y estadísticas

- Banco Central de Bolivia. [Estadísticas Semanales, listado oficial de Excel](https://www.bcb.gob.bo/?q=estad-sticas-semanales). Fuente de variables monetarias, financieras y cambiarias del proyecto; consulta del repositorio y corte de datos indicados al inicio.
- Banco Central de Bolivia. [Glosario de términos económico financieros](https://www.bcb.gob.bo/webdocs/seccioneducativa/GLOSARIO%20DE%20TE%CC%81RMINOS%20ECONO%CC%81MICO%20FINANCIEROS%20.pdf). Definiciones de RIB y RIN.
- Banco Central de Bolivia. [Vigencia del valor referencial del dólar](https://www.bcb.gob.bo/?q=node%2F238466); [nuevo tipo de cambio oficial](https://www.bcb.gob.bo/?q=node%2F240202); [serie y vigencia del TCO](https://www.bcb.gob.bo/bcb_tco_publico_ultima_cotizacion.php).
- Banco Central de Bolivia. [Tabla histórica de precios de activos virtuales, 2024](https://www.bcb.gob.bo/webdocs/activos_virtuales/HISTORICO.pdf). Nota sobre Tether ponderado por volumen de P2P.
- Instituto Nacional de Estadística de Bolivia. [Documento metodológico del IPC base 2016](https://www.ine.gob.bo/index.php/descarga/171/metodologia/37244/documento-metodologico-ipc-2016.pdf).
- Fondo Monetario Internacional. [Manual de Balanza de Pagos y Posición de Inversión Internacional, sexta edición, BPM6](https://data.imf.org/-/media/iData/External-Storage/Documents/73FBCD5B6CDE4D289C60B9B0CAA40622/en/2-bpm6.pdf). Definición internacional de activos de reserva.
- Fondo Monetario Internacional. [Metodología de índice de presión cambiaria](https://www.elibrary.imf.org/view/journals/007/2010/040/article-A001-en.xml). Referencia conceptual; el índice de este proyecto no reproduce su fórmula.
- paralelo.bo. [Histórico CSV](https://paralelo.bo/api/v1/historical.csv) y [metodología, cobertura y bitácora de cambios](https://paralelo.bo/metodologia). Datos abiertos CC BY 4.0; atribución: paralelo.bo.

### Fundamentos econométricos y documentación de implementación

- Dickey, D. A. y Fuller, W. A. (1979). [*Distribution of the Estimators for Autoregressive Time Series with a Unit Root*](https://doi.org/10.1080/01621459.1979.10482531), *Journal of the American Statistical Association*, 74(366a), 427-431.
- Granger, C. W. J. (1969). [*Investigating Causal Relations by Econometric Models and Cross-spectral Methods*](https://doi.org/10.2307/1912791), *Econometrica*, 37(3), 424-438.
- Hyndman, R. J. y Athanasopoulos, G. [Validación temporal](https://otexts.com/fpptr/tscv.html) y [criterio de fuerza estacional](https://otexts.com/fpptr/stationarity.html), *Forecasting: Principles and Practice*.
- SciPy. [Prueba de Levene centrada en la mediana](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.levene.html), variante Brown-Forsythe usada para H3.
- statsmodels. [Prueba ADF](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.adfuller.html), [SARIMAX](https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.sarimax.SARIMAX.html), [Ljung-Box](https://www.statsmodels.org/dev/generated/statsmodels.stats.diagnostic.acorr_ljungbox.html) y [prueba de Granger](https://www.statsmodels.org/v0.14.4/generated/statsmodels.tsa.stattools.grangercausalitytests.html). Documentación de las funciones usadas, no sustituto de una validación económica.

### Material reproducible del repositorio

- [`bcb_pipeline/`](../bcb_pipeline/): descarga, parseo, consolidación, PDF, capturas y series históricas.
- [`stress_monitor/`](../stress_monitor/): variables derivadas, pruebas, Markov, pronósticos, brecha, simulación e informe automático.
- [`notebooks/`](../notebooks/): seis cuadernos ejecutados por capítulo.
- [`app/streamlit_app.py`](../app/streamlit_app.py): tablero de siete pantallas.
- [`data/external/sources.json`](../data/external/sources.json): procedencia y huellas SHA-256 de los dos CSV externos.
- [`reports/results.json`](results.json): cifras exactas del corte utilizado en este informe.
