# Guion de presentación (10 min)

**Mensaje central:** Bolivia cambió de régimen cambiario en 2026; construimos un monitor que lo mide con procesos estocásticos y series de tiempo, y encontramos que una cifra muy citada (la caída de la bolivianización) es un efecto de valoración.

## Diapositivas
1. **Problema y oportunidad** – del tipo fijo 6,96 al oficial flexible (29-jun-2026); quién necesita monitorear (PYMES importadoras, cooperativas, analistas).
2. **Datos** – Excel semanal del BCB (1987→hoy, ~170 variables), PDF de activos virtuales, DolarApi. Pipeline automático.
3. **Hallazgo 1: efecto de valoración** – gráfico `fig_valoracion.png`: 92,1→88,3 (vigente) vs 92,1→92,9 (constante); depósitos en USD planos.
4. **Cap. 3 – Cadena de Markov** – índice de estrés, 3 estados, matriz P, permanencia, probabilidades a 1/3/6 meses; validación con episodios.
5. **Cap. 6 – SARIMA + validación honesta** – dónde gana y dónde no (reservas: gana el ingenuo).
6. **Cap. 7 – Monte Carlo** – probabilidad de cruzar un umbral de reservas; simulador de costo en Bs.
7. **Demo en vivo** – semáforo → reservas → simulador (caso: factura de USD 10.000 a 90 días).
8. **Limitaciones y siguientes pasos** – historial P2P pendiente (H1/H5), GARCH, más datos del régimen flexible; modelo de negocio (suscripción con alertas semanales).

## Demo (orden sugerido)
`streamlit run app/streamlit_app.py` → *Semáforo* (mover umbrales) → *Reservas y depósitos* (umbral Monte Carlo) → *Simulador* → *Brecha* con interruptor DEMO (decir explícitamente que son datos simulados).

## Preguntas probables y respuestas honestas
- **¿Por qué «Estable» si hay tensión cambiaria?** El índice usa reservas y bolivianización; la tensión cambiaria vive en el paralelo. Por eso la brecha es el siguiente componente.
- **¿Los estados son predicciones?** No: son descriptivos y relativos (percentiles de 1989-2026).
- **¿Es Markov de primer orden?** Se rechaza frente a orden 2 (p<0,05); es una aproximación útil para persistencia y probabilidades.
- **¿Por qué SARIMA no gana en reservas?** Quiebres estructurales (2015, 2020, 2023-26); el último valor es difícil de superar; los IC cubren menos de 95%.
- **¿Y el dólar paralelo?** Pipeline y análisis listos; falta acumular historial P2P (PDF del BCB + recolector). Mientras tanto la pantalla usa datos DEMO etiquetados.
- **¿Cómo se vende?** Suscripción con semáforo gratuito y alertas/reportes pagos; ventaja: serie P2P propia y base de versiones del BCB.
