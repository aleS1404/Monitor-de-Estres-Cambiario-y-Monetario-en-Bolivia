# Guion de presentación (10 min)

**Mensaje central:** Bolivia cambió de régimen cambiario en 2026; construimos un monitor que lo mide con procesos estocásticos y series de tiempo, y encontramos que una cifra muy citada (la caída de la bolivianización) es un efecto de valoración.

## Diapositivas
1. **Problema y oportunidad** – del tipo fijo 6,96 al oficial flexible (29-jun-2026); quién necesita monitorear (PYMES importadoras, cooperativas, analistas).
2. **Datos** – Excel semanal del BCB, TCO diario del BCB y 830 fechas de mediana P2P histórica de paralelo.bo (CC BY 4.0); PDF y DolarApi se conservan por separado. Mostrar `data/external/sources.json` para procedencia.
3. **Hallazgo 1: efecto de valoración** – gráfico `fig_valoracion.png`: 92,1→88,5 (vigente) vs 92,1→93,0 (constante); depósitos en USD 2.654→2.578 MM. Fechas: sep-2025→oct-2026.
4. **Cap. 3 – Cadena de Markov** – índice de estrés, 3 estados, matriz P, permanencia, probabilidades a 1/3/6 meses; validación con episodios.
5. **Cap. 6 – SARIMA + validación honesta** – dónde gana y dónde no (reservas: gana el ingenuo).
6. **Cap. 7 – Monte Carlo** – probabilidad de cruzar un umbral de reservas; simulador de costo en Bs.
7. **Brecha y pruebas H1/H3/H5** – H1: φ=0,842, vida media 4,0 días, ADF p=8,86e-5 (138 días post-flexible). H3: σ diaria 0,47%→1,12%, razón 2,39, Levene p=3,82e-5 (56/67 retornos de misma metodología). H5: correlación máxima k=+1 día hábil, 0,658; Granger lag 1 paralelo→oficial p=9,21e-10 y reverso p=0,293 (97 retornos). Es asociación predictiva, no causalidad; el horario de publicación importa.
8. **Demo en vivo** – semáforo → brecha observada → reservas → simulador (factura de USD 10.000 a 90 días).
9. **Limitaciones y siguientes pasos** – la mediana P2P anterior a mayo-2026 es reconstruida, la metodología cambió en septiembre, H5 puede reflejar el calendario de publicación; ampliar seguimiento y considerar GARCH como extensión.

## Demo (orden sugerido)
`streamlit run app/streamlit_app.py` → *Semáforo* (mover umbrales) → *Brecha* (fuentes y H1/H3/H5 con datos observados) → *Reservas y depósitos* (umbral Monte Carlo) → *Simulador*. Mantener el interruptor DEMO apagado.

## Preguntas probables y respuestas honestas
- **¿Por qué «Estable» si hay tensión cambiaria?** El índice usa reservas y bolivianización neutralizada y conserva los mismos componentes desde 1989; la brecha P2P reciente se analiza por separado.
- **¿Los estados son predicciones?** No: son descriptivos y relativos (percentiles de 1989-2026).
- **¿Es Markov de primer orden?** Se rechaza frente a orden 2 (p<0,05); es una aproximación útil para persistencia y probabilidades.
- **¿Por qué SARIMA no gana en reservas?** Quiebres estructurales (2015, 2020, 2023-26); el último valor es difícil de superar; los IC cubren menos de 95%.
- **¿De dónde sale el paralelo?** Mediana diaria histórica de anuncios P2P de paralelo.bo (CC BY 4.0), con 830 fechas y copia/hash verificable. No es una transacción ejecutada ni la cotización de Binance.
- **¿H5 prueba que el paralelo causa el oficial?** No. Correlación cruzada y Granger miden adelanto y poder predictivo condicional. El momento de publicación puede producir el rezago observado.
- **¿Cómo se vende?** Suscripción con semáforo gratuito y alertas/reportes pagos; ventaja: serie P2P propia y base de versiones del BCB.
