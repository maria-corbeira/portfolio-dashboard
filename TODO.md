# Pendientes del dashboard

- [ ] **El calendario de resultados sale vacío.** De los dos endpoints de Nasdaq, el
  de `earnings-date` daba 404 en los 15 tickers y se ha retirado. El que queda
  (`quote/{t}/eps`) responde 200, pero su JSON no trae ninguna de las tres claves que
  busca la regex (`reportDate`, `date`, `announcementDate`), así que no sale ninguna
  fecha. Vacío es lo correcto frente a inventado, pero hoy no hay ninguna fuente de
  fechas de resultados que funcione: hay que encontrar otra o leer la estructura real
  de ese JSON.
- [ ] **Toggle inglés / español en las noticias.** Ahora los titulares salen en el
  idioma de origen porque el Action los copia tal cual. La idea es un botón que
  cambie el idioma de toda la vista. Implica guardar una traducción por titular:
  o se traduce en el propio Action (haría falta un servicio de traducción con
  clave) o se traduce por lotes cuando hablemos y se cachea en `news.json` bajo
  una clave `title_es`. La segunda opción no cuesta dinero pero solo cubre lo que
  se haya revisado.
- [x] ~~Precios históricos de NVDA~~ — hecho el 6-sep-2026. Ya hay P/E por ejercicio
  de las seis empresas analizadas. **Ojo, no se usó `period=Monthly`**: el ejercicio de
  NVIDIA cierra el último domingo de enero, que casi nunca es fin de mes, y en FY2025 el
  cierre mensual (120,07 el 31-ene-2025, ya con la caída de DeepSeek) se desviaba un 18%
  del cierre a fecha fiscal (142,62 el 24-ene-2025). Se usó `period=Weekly`, cuya fila va
  etiquetada con el primer día hábil de la semana y cuyo campo `c` es el cierre del
  **último** día hábil de esa semana: se toma la fila de la semana que contiene el viernes
  anterior al domingo de cierre. Los diez valores se verificaron uno a uno contra el precio
  sin ajustar (×40 antes del split de jul-2021, ×10 antes del de jun-2024).
- [ ] **Inversiones a corto de NVIDIA en FY2026.** No existen bajo ninguno de los
  tres tags habituales; el último hecho es de octubre de 2025. Sin ese dato, el
  ROIC y la deuda neta de FY2026 salen n.d. Probablemente cambiaron de etiqueta
  en el 10-K.
- [ ] **Amortización de Microsoft.** Los dos tags estándar dan 404 y el disponible
  solo cubre inmovilizado. Sin eso no hay EBITDA ni Deuda neta/EBITDA de MSFT.
- [x] ~~RSI y media de 200 sesiones~~ — hecho. `scripts/history.py` acumula el
  cierre diario en `prices_history.json` y calcula RSI de 14 y media de 200. El RSI
  aparecerá a las 15 sesiones desde la primera pasada del Action; la media de 200,
  a las 200 (unos diez meses). Hasta entonces salen n.d., no aproximados.
- [ ] **Precios objetivo de la watchlist.** Los sembré con el extremo bajo del rango
  de valor intrínseco de cada una (PGR 180, V 290, PLTR 28, LULU 190, UNP 159,
  SHEL 69). Son propuestas mías, no tuyas: revísalos.
- [ ] **Fuente de top movers sin verificar.** Se prueban tres en cascada
  (Nasdaq marketmovers y los dos screeners de Yahoo). Sigue sin comprobarse, pero
  ahora se sabe más: en la pasada del 6-sep-2026 Nasdaq **sí respondió** (aparece en
  `top_movers_fuente`) y devolvió la tabla vacía porque era **domingo, con el mercado
  cerrado**. No es que la fuente esté rota. Los errores de las otras dos se perdían
  porque `data.json` solo los volcaba `if failed:`, y `failed` cuenta únicamente
  precios: ya está arreglado, se vuelcan siempre. **Para decidir hace falta una pasada
  en día hábil**, y luego leer `errors` de `data.json`. Ejecutar `probe.yml` sirve para
  saber si responden, pero en fin de semana no distingue "rota" de "sin datos hoy".
- [ ] **Las 6 posiciones que faltan por analizar con datos de la SEC**: AMZN, AAPL,
  IBM, COP, WMT, CVX. Hoy tienen scores de búsqueda web de la primera sesión.
