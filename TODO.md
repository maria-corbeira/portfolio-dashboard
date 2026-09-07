# Pendientes del dashboard

- [x] ~~**El calendario de resultados sale vacío**~~ — arreglado el 7-sep-2026, **pendiente de
  verificar en producción**. El probe de noticias que corrió Maria destapó la fuente buena:
  `api.nasdaq.com/api/calendar/earnings?date=YYYY-MM-DD` responde **200 con 6.523 bytes** y trae
  `data.rows` con `symbol`, `time`, `epsForecast` y `fiscalQuarterEnding`. Es un calendario
  **por día**, no por ticker, que es justo por lo que no se había encontrado antes: los dos
  endpoints que se probaban eran por ticker (`company/{t}/earnings-date`, retirado con 404, y
  `quote/{t}/eps`, que responde 200 pero no trae ninguna fecha). `calendario_resultados()` ahora
  recorre los 45 días siguientes saltando fines de semana y parando en cuanto todos los tickers
  tienen fecha: unas 33 peticiones en el peor caso. **No se ha podido probar contra Nasdaq desde
  la sesión** (el proxy de egress da 403 a ese dominio); sí se probó la lógica de parseo contra
  una respuesta sintética con la forma observada, incluidos los casos de JSON corrupto y de
  respuesta vacía, que salen vacíos sin romper. Falta que corra `news.yml` una vez y comprobar
  que `news.json` trae `calendario` con fechas. Ojo: el `items: 0` del probe no significa nada,
  cuenta elementos `<item` de RSS y esto es JSON.
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
- [ ] **Fuente de top movers: sigue sin poder decidirse, y ya van dos intentos.** El 7-sep-2026
  hubo pasada con el mercado **cerrado otra vez**: es el primer lunes de septiembre, o sea el
  Labor Day estadounidense. Se confirma mirando `data.json`, donde los 22 precios traen
  `market_time: null` y coinciden al céntimo con el cierre del viernes 4 (MSFT 499,70 y −2,04%,
  idénticos a los del probe del día 5). Lo que sí se aprendió: **Nasdaq no está rota**, respondió
  y aparece en `top_movers_fuente`, y devolvió tabla vacía porque no había sesión; los dos
  screeners de Yahoo, en cambio, dieron **429**, no un fallo de formato, así que ahí el problema
  es límite de peticiones y no que el endpoint haya desaparecido. El mismo 429 salió en
  `yahoo_spark` para NVDA y SHEL, aunque el respaldo de CNBC cubrió los 22 tickers y `failed`
  quedó vacío. **Hace falta una pasada en día de mercado abierto de verdad** — martes 8 en
  adelante — y volver a leer `errors` y `top_movers` de `data.json`. Aviso para la próxima: correr
  el workflow en festivo no distingue "rota" de "sin datos hoy", que es exactamente lo que ha
  pasado las dos veces.
- [x] **Las doce posiciones analizables ya tienen 10 años de datos de la SEC.** Se cerró el
  7-sep-2026 con COP (61/100, Observar). Las doce salen **Observar**: ninguna Comprar y ninguna
  Evitar. Eso no es un empate, es un resultado: en las de calidad alta el freno es siempre el
  precio, y en las dos petroleras es la calidad. Merece una conversación con Maria sobre qué
  hacer con el dinero nuevo, porque el marco no está señalando ningún sitio donde ponerlo.
- [ ] **Los 4 ETF de `outsideFramework` siguen sin analizar** y no les aplica este scoring. Si
  alguna vez se quiere una vista real de concentración, hace falta su composición, que hoy no
  se estima a propósito.
- [ ] **Arrendamientos de COP: ausencia no verificada.** Ni los cuatro tags nuevos ni los dos
  antiguos devuelven nada en ningún ejercicio, así que la deuda total está algo infravalorada.
  No se puso un cero. Se cerraría leyendo la nota de arrendamientos de un 10-K por la vía de
  las páginas R.
- [ ] **Retribución en acciones de COP sin etiquetar**, igual que en CVX: `sbc_pct_revenue`
  sale n.d. en las dos petroleras.
- [ ] **El marco de puntuación castiga a las cíclicas por construcción.** CVX saca 45 en
  calidad porque el umbral de ROIC del 12% y el de ROE del 15% no tienen sentido para una
  productora de materia prima que perdió dinero en 2016 y 2020 y ganó 35.465 M$ en 2022. Está
  dicho en su ficha, pero convendría decidir si el marco lleva un ajuste sectorial explícito
  (p. ej. ROIC medio del ciclo completo en vez del de cinco años) o si se deja así y el aviso
  en la ficha basta. Afecta también a COP.
- [ ] **Retribución en acciones de CVX sin etiquetar.** `ShareBasedCompensation` da 404 en los
  diez ejercicios, así que `sbc_pct_revenue` sale n.d. No afecta al scoring, pero conviene
  saberlo si algún día se compara la dilución entre posiciones.
- [ ] **La amortización de CVX en 2019 incluye deterioros** (29.218 M$ frente a unos 19.400 los
  años vecinos), así que el EBITDA de ese ejercicio está inflado y la deuda neta/EBITDA de 2019
  sale mejor de lo que fue. Está dicho en la ficha. Si se quiere separar, hay que buscar el tag
  de deterioros y restarlo.
- [ ] **Gasto financiero de AAPL en FY2024 y FY2025.** El tag InterestExpense se corta en
  FY2023 y los fallbacks no cubren esos dos años, así que la cobertura de intereses sale n.d.
  En FY2023 era de 29,1 veces y la deuda a largo ha bajado de 95.281 a 78.328 M$ desde
  entonces, así que no hay motivo de alarma: falta el dato, no la solvencia. Mismo caso que
  AMZN, justo debajo.
- [ ] **Dividendos de AAPL en FY2016-FY2017 con un tag distinto al del resto de la serie.**
  El extractor usó PaymentsOfDividendsCommonStock (11.965 y 12.563 M$) para esos dos años y
  PaymentsOfDividends (que en esos mismos años vale 12.150 y 12.769) para FY2018-FY2025. La
  diferencia es del 1,5% y solo afecta al payout de dos ejercicios, pero mezcla definiciones:
  el segundo tag incluye los dividendos equivalentes de las acciones restringidas, que es la
  línea que Apple presenta en su estado de flujos. Si se toca, unificar en PaymentsOfDividends
  los diez años. Está anotado en `avisos` de AAPL_cf.json.
- [ ] **Gasto financiero de AMZN en FY2025.** Los cuatro tags probados (InterestExpense,
  InterestExpenseDebt, InterestIncomeExpenseNet e InterestExpenseNonoperating) no tienen
  ningún hecho con `end=2025-12-31`; InterestAndDebtExpense da 404. La cobertura de
  intereses del último ejercicio sale n.d. y el bloque de Salud se pondera sobre los otros
  tres umbrales. En 2024 era de 28,5 veces, así que no hay motivo para pensar que el dato
  sea malo: simplemente no está etiquetado todavía. Revisar cuando la SEC actualice.
- [ ] **Capitalización por ejercicio, sin calcular en NINGUNA empresa.** `build_src.py`
  escribe `"Market Cap (MM)": [None] * n`, así que `metrics.py` deja `market_cap` y
  `fcf_yield` vacíos en los diez ejercicios de las nueve compañías. El P/E histórico sí
  sale, porque se calcula como precio / BPA. Ya hay precios de cierre por ejercicio en
  `fundamentals/raw/_precios.json` y acciones diluidas por año, así que es una
  multiplicación: `market_cap = precio_cierre x acciones_diluidas`. Desbloquearía la serie
  histórica de FCF yield, que hoy solo existe para el ejercicio en curso y recalculada con
  el precio en vivo.
- [ ] **ROIC de IBM incompleto.** Solo se calcula en 6 de los 10 ejercicios: en 2020, 2022,
  2024 y 2025 IBM tuvo ingreso fiscal neto, el tipo efectivo sale negativo y `metrics.py` lo
  invalida a propósito (solo acepta el rango 0-60%). No es un fallo de extracción, es que la
  fórmula NOPAT = EBIT x (1 - tipo) no significa nada con un tipo negativo. Si se quiere ROIC
  en esos años habría que decidir un criterio (¿tipo normalizado?) y dejarlo escrito.
- [ ] **Capex de IBM sin el software capitalizado.** IBM dejó de etiquetarlo en XBRL después
  de 2016 y no hay tag us-gaap que lo recoja, así que su FCF está algo sobrestimado. Está
  dicho en la ficha. Si aparece la cifra, va a `rows.capex` sumada al inmovilizado.
- [ ] **Constellation: solo 4 ejercicios, y faltan 2016-2021.** Están en los PDF anuales de
  `csisoftware.com` (los `Q4<NN>` de 2017 a 2021, localizables por la API REST de WordPress del
  sitio) y se leen con `pypdf` igual que los dos ya usados. Con diez años su score sería
  comparable al de las doce, y sobre todo se vería el ROIC **antes** de las escisiones de Topicus
  (2021) y Lumine (2023), que es la pregunta de verdad: si la máquina ya se estaba desacelerando
  antes de repartirse.
- [ ] **Constellation: el tipo impositivo de 2023 invalida su ROIC.** Fue del 77% por el gasto de
  las acciones preferentes rescatables (597 M$), y `metrics.py` solo acepta el rango 0-60%, así
  que ese año sale n.d. Es el mismo problema que el de IBM y se arreglaría con el mismo criterio,
  si algún día se decide uno.
- [ ] **Constellation cotiza en CAD y la ficha está en USD.** Sus cuentas están en dólares
  estadounidenses, así que las métricas son correctas, pero el precio que sigue el dashboard es el
  de CNSWF en el OTC, que es poco líquido: el 7-sep-2026 marcaba 2.175,00 $ frente a 3.023,96 CAD
  en Toronto (FX implícito 1,390, coherente). Si algún día CNSWF deja de cotizar días enteros,
  habrá que decidir si se convierte el precio de la TSX en vez de leer el OTC.
