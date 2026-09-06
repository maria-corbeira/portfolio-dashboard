# Pendientes del dashboard

- [ ] **Toggle inglés / español en las noticias.** Ahora los titulares salen en el
  idioma de origen porque el Action los copia tal cual. La idea es un botón que
  cambie el idioma de toda la vista. Implica guardar una traducción por titular:
  o se traduce en el propio Action (haría falta un servicio de traducción con
  clave) o se traduce por lotes cuando hablemos y se cachea en `news.json` bajo
  una clave `title_es`. La segunda opción no cuesta dinero pero solo cubre lo que
  se haya revisado.
- [ ] **Precios históricos de NVDA.** Es lo único que falta para tener el P/E por
  ejercicio de las seis empresas analizadas. Se cortó al agotarse el límite de
  WebFetch. Fuente: `https://stockanalysis.com/api/symbol/s/nvda/history?range=10Y&period=Monthly`,
  tomando la fila de enero de cada año (NVIDIA cierra el último domingo de enero).
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
  (Nasdaq marketmovers y los dos screeners de Yahoo). Ninguna está comprobada
  todavía: hay que ejecutar `probe.yml` y mirar `probe_news.json`.
- [ ] **Las 6 posiciones que faltan por analizar con datos de la SEC**: AMZN, AAPL,
  IBM, COP, WMT, CVX. Hoy tienen scores de búsqueda web de la primera sesión.
