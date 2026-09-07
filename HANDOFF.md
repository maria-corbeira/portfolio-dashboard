# Hand-off — dashboard de cartera de Maria

Para el agente que continúe en Claude Code. **Léelo entero antes de tocar nada.**
Contiene errores ya cometidos y resueltos: repetirlos cuesta horas.

Actualizado el 6-sep-2026, después del primer push y de la primera ejecución real
de los GitHub Actions.

---

## 0 · Empieza por aquí

```bash
cd ~/Claude/Investing/portfolio-dashboard
git log --oneline -5        # dónde estamos
cat TODO.md                 # la lista de pendientes, en casillas
git status -sb              # ¿hay algo sin subir?
```

Luego mira la pestaña **Actions** del repo en GitHub: si algo está en rojo, eso es
lo primero.

---

## 1 · Qué es esto

Un dashboard de cartera en un solo `index.html`, publicado desde
`github.com/maria-corbeira/portfolio-dashboard`. Tres GitHub Actions lo alimentan.
Maria decide con él si mantener, ampliar o vender.

**No es un juguete: se toman decisiones de inversión con estos números.** La regla que
gobierna el proyecto entero es que un dato que no se ha podido obtener sale como `n.d.`
y se explica por qué. Nunca se rellena con una estimación, una media ni un cero.

### Estado a 7-sep-2026

- **Repo sincronizado.** El primer push se hizo hoy; local y GitHub están idénticos.
- **El Action de precios funciona.** Primera pasada real: 21 tickers, todos vía CNBC.
- **El de noticias y el probe no han corrido todavía.** Maria tiene que lanzarlos a
  mano una vez (Actions → Run workflow). Hasta entonces `news.json` no existe y el
  panel de Home sale con su estado vacío, que es lo correcto.
- 15 posiciones reales, 7 candidatas en watchlist (la séptima, Constellation, entró el 7-sep-2026).
- **LAS DOCE empresas analizadas con 10 años de la SEC**: GOOGL, MSFT, META, UBER, ISRG,
  NVDA, WMT, IBM, AMZN, AAPL, CVX y COP. Ya no queda ninguna con score de búsqueda web. Los
  4 ETF de `outsideFramework` no entran en el scoring por diseño.
- **Las doce tienen P/E por ejercicio.** Los precios históricos de NVDA se cerraron el
  6-sep-2026; con ellos aparece también su P/E frente a la mediana de 10 años (mediana
  50,9; hoy −8%).
- **Lo que va saliendo:** WMT 63/100 y IBM 58/100, las dos Observar y por motivos
  opuestos — Walmart es un buen negocio a precio de buen negocio, IBM un negocio flojo a
  precio sensato. AMZN 70/100, también Observar: calidad en aumento (margen operativo del
  3,1% al 11,2% en diez años) con la valoración sin colchón, porque el capex de IA se come
  el flujo libre. AAPL 72/100, Observar: **95 sobre 100 de calidad, el mejor negocio de la
  cartera, y los tres criterios de valoración fallando a la vez** (P/E 42,9, PEG 2,39, FCF
  yield 2,06%). CVX 52/100 y COP 61/100, las dos Observar, y son el caso distinto: aquí falla la
  calidad, no el precio. En las dos petroleras el balance saca 82 y el FCF yield aprueba;
  COP además pasa el P/E, cosa que CVX no.
- **Constellation Software (CNSWF) en watchlist, 75/100, Observar — y es el primer caso
  de una empresa que NO presenta ante la SEC.** Es canadiense (TSX: CSU), reporta en dólares
  bajo IFRS y no tiene 10-K: los datos salen de sus cuentas anuales auditadas por KPMG, en PDF,
  leídas con `pypdf` (ver sección 5). Son **4 ejercicios (2022-2025), no 10**, así que su score
  no es directamente comparable con el de las doce. Lo interesante del caso: el P/E de 90 veces
  dice "carísima" y el EV/FCF de 20 veces dice "razonable", y la diferencia entera es la
  amortización de intangibles de adquisiciones (1.182 M$ sobre 11.623 de ventas). El ROIC se
  publica al 20,6% y en caja es del 33%. Su riesgo real no es el múltiplo: es que el gasto en
  adquisiciones lleva tres años bajando mientras la caja generada casi se dobla.

- **LAS DOCE SALEN OBSERVAR.** Ninguna Comprar, ninguna Evitar. No es un empate, es un
  resultado: en las de calidad alta el freno es siempre el precio, y en las dos petroleras es
  la calidad. **Conviene hablarlo con Maria**, porque el marco no está señalando ningún sitio
  donde poner dinero nuevo, y eso es información aunque no sea una recomendación.

---

## 2 · Las tres skills

Están en la cuenta de Maria y son la forma correcta de trabajar:

| Skill | Para qué |
|---|---|
| `analisis-value-quality` | El framework de scoring 0-100 y el formato de respuesta |
| `datos-sec-10anios` | Extraer 10 años de estados financieros de la SEC |
| `dashboard-cartera` | Mantener este repo |

Úsalas. Recogen decisiones que costaron sesiones enteras.

---

## 3 · Arquitectura

```
index.html            TODO el dashboard: datos, estilos y lógica en un fichero (112 KB)
  holdings[]          12 acciones en cartera
  outsideFramework[]  QQQ, VOO, IAUM — el scoring de empresa no les aplica
  watchlist[]         6 candidatas, con `target` = precio de entrada objetivo
  const fundamentals  incrustado entre // <<<FUNDAMENTALS y // FUNDAMENTALS>>>
  3 paneles           #tab-home · #tab-stocks · #tab-watch

data.json             precios + indicadores + movimientos fuertes + top movers
prices_history.json   cierre diario por ticker, 420 sesiones (empieza a acumular ahora)
news.json             noticias por ticker y de mercado, calendario de resultados
eventos.json          keynotes y presentaciones, CURADO A MANO
probe.json            qué fuentes de precios responden desde las IPs de Actions
probe_news.json       ídem para noticias y top movers (aún no generado)
fundamentals/
  raw/                las 16 extracciones de la SEC con sus tags y avisos
  raw/_precios.json   cierres por ejercicio, para el P/E histórico
  <T>.src.json        10 ejercicios en formato plantilla IDC
  <T>.json            métricas calculadas
scripts/
  fetch_prices.py     precios; prices.yml cada 15 min
  history.py          histórico, variaciones, RSI de 14, media de 200
  fetch_news.py       noticias; news.yml cada 6 h
  load_raw.py         extracciones de GOOGL/MSFT/META
  load_raw2.py        ídem UBER/ISRG/NVDA, y aplica los splits
  build_src.py        crudo -> formato IDC
  metrics.py          formato IDC -> métricas del scoring
  embed_fundamentals.py  incrusta fundamentals/*.json en index.html
  probe.py / probe_news.py  comprueban fuentes desde las IPs de Actions
```

Cadena para añadir una empresa:

```bash
# 1. extraer de la SEC con subagentes (skill datos-sec-10anios)
# 2. meter el resultado en scripts/load_raw2.py
python3 scripts/load_raw2.py
python3 scripts/build_src.py
python3 scripts/metrics.py fundamentals/<T>.src.json -o fundamentals/<T>.json
python3 scripts/embed_fundamentals.py
```

---

## 4 · Reglas que no se negocian

**Un vacío no es un cero.** `metrics.py` trataba una caja vacía como cero al calcular el
capital invertido y hundía el ROIC de Microsoft en FY2016-17 (16,6% en vez de ~50%). Si
falta un componente, propaga el vacío.

**Verifica cada sustitución de texto.** Editar `index.html` con `str.replace` sin
comprobar el número de coincidencias hace que un cambio se pierda en silencio. Ha pasado
dos veces. Usa siempre este patrón:

```python
def sust(p, viejo, nuevo, etiqueta):
    s = p.read_text(encoding="utf-8")
    n = s.count(viejo)
    assert n == 1, f"{etiqueta}: {n} coincidencias, se esperaba 1"
    p.write_text(s.replace(viejo, nuevo, 1), encoding="utf-8")
```

Y **un `assert` que falla aborta el script antes de escribir**: si pones varios cambios
en un mismo bloque, los anteriores se pierden. Escribe cada uno por separado, como arriba.

**Comprueba el JS y RENDERIZA antes de dar nada por bueno.**

```bash
python3 -c "s=open('index.html',encoding='utf-8').read(); a=s.index('<script>')+8; b=s.rindex('</script>'); open('/tmp/app.js','w').write(s[a:b])"
node --check /tmp/app.js
```

Un error habitual al reemplazar una línea de un array es **comerse la coma final**, y el
fallo aparece señalando la línea siguiente. Después levanta un `http.server` y abre la
página con Playwright (`chromium` preinstalado, `PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers`),
captura `pageerror`, despliega filas y **comprueba las cifras contra un cálculo aparte**.
Con `file://` la carga de los JSON falla por CORS.

Cuatro errores llegaron hasta la captura de pantalla y solo se vieron ahí: un `$` perdido,
un `"% pp"` duplicado, un treemap que codificaba el área al revés y una etiqueta repetida
en todas las filas.

**Cuidado con `index.html` como fuente de datos.** `fetch_prices.py` y `fetch_news.py`
sacan los tickers del propio HTML con una expresión regular. Si defines en otro sitio una
clave con el mismo nombre que la del ticker y valor en mayúsculas, se cuela como si fuera
una acción. Pasó con el título de la minificha del ROIC. La regex está acotada ahora a la
región de los tres arrays, pero **no reutilices esa clave** fuera de ellos.

**Los gráficos codifican, no decoran.** El área del treemap es el peso real de la posición
(desvío máximo medido: 0,4 puntos). Los huecos se dibujan como huecos: NVIDIA no tiene FCF
antes de FY2022 y la línea se corta en vez de interpolar. Si el último valor de una serie
no es el del ejercicio más reciente, se etiqueta con su año.

**Color: nunca la única señal.** El verde puro contra el rojo falla la validación de
daltonismo (ΔE 4,6 en deuteranopía, indistinguibles). Se usa el aqua de la paleta validada
y cada casilla lleva siempre el número con signo. Para validar una paleta nueva usa la
skill `dataviz` y su `scripts/validate_palette.js`. **No lo estimes a ojo, ejecútalo.**

**El periodo mensual miente si el ejercicio no cierra a fin de mes.** Para `_precios.json`
se usó `period=Monthly` con MSFT, META, UBER e ISRG, y ahí vale: todas cierran el último
día de un mes. NVIDIA cierra el **último domingo de enero**, que casi nunca coincide: en
FY2025 el cierre mensual eran 120,07 (31-ene-2025, ya con la caída de DeepSeek del día 27)
frente a los 142,62 del cierre a fecha fiscal (24-ene-2025). Un 18% de desviación, que
falsea el P/E de ese ejercicio. Para estos casos usa `period=Weekly`: **la fila va
etiquetada con el primer día hábil de la semana y su campo `c` es el cierre del último día
hábil de esa semana**, así que se toma la fila de la semana que contiene el último día
hábil anterior al cierre fiscal. Antes de dar por buena la interpretación, compruébala:
la fila `2025-01-21` vale 142,62, que es el cierre del viernes 24, no el del martes 21.

**Los números se pintan en español, y solo con los helpers.** Toda cifra visible sale por
`money`, `sign`, `num` o `cant` (y `fMill` para los gráficos), que ya aplican coma decimal y
punto de millar. **Nunca uses `toFixed()` para pintar un número**: escribe el punto decimal
inglés, y así llegaron a producción `215.9 B$` en los gráficos de Ventas y FCF, `$230.36`
en los precios y `▲0.84%` en la variación del día. `toFixed()` solo vale para coordenadas
SVG y píxeles de CSS, que sí llevan punto — son las únicas siete que quedan en el fichero.

Y dos trampas al tocar esto:

- **`es-ES` no agrupa los números de cuatro cifras.** `(6910).toLocaleString('es-ES')`
  devuelve `6910`, no `6.910`. No es un fallo de Intl: es la regla ortográfica del español.
  Aquí se agrupa igualmente, a propósito, porque en una tabla de cifras comparables un
  `6910` entre un `11.716` y un `215.938` descuadra la lectura. Lo hace `agrupa()`, a mano,
  porque `minimumGroupingDigits` no está soportado en todas las implementaciones.
- **Nunca lances un reemplazo global de `.` por `,` sobre `index.html`.** Los datos son
  literales JS en el mismo fichero: `price:366.25` y `shares:1.61` **tienen** que llevar
  punto, y cambiarlos rompe la página entera. Acota la sustitución al interior de las
  cadenas (`note:"..."`) y **excluye los separadores de miles**: convertir `96.676 M$` en
  `96,676` divide la cifra por mil sin que nada falle. La salvaguarda que funciona es
  tocar solo los puntos seguidos de una o dos cifras, porque un separador de millar
  siempre lleva tres. Revisa la lista de coincidencias antes de escribir, no después.

**WebFetch resume con un modelo pequeño, y ese modelo se inventa cifras.** Al pedirle
directamente las diez fechas de NVDA, **cinco de las diez respuestas estaban mal**: unas
desplazadas una semana y una — 144,47 para enero de 2024 — sencillamente inventada, cuando
el valor real era 61,03. Las inventadas son plausibles, así que no se detectan leyéndolas.
Lo que funciona: pedir **todas las filas de una ventana, verbatim y sin resumir**, quedarse
con la que toca uno mismo, y validar cada valor contra una referencia independiente. Aquí
fueron los precios sin ajustar, multiplicando por 40 antes del split de julio de 2021 y por
10 antes del de junio de 2024. Es la misma disciplina de anclas de los subagentes de la
sección 5, y por el mismo motivo.

**Persigue los huecos: pueden cambiar el veredicto.** En COP faltaban las inversiones a corto
de 2021 y 2022. Con el hueco, el ROIC medio de cinco años salía 13,8%; al cerrarlo, 18,1%. Es
la diferencia entre suspender y aprobar el umbral del 12%, en la pata que pesa el 40%. Dos
llamadas a una página R lo resolvieron. **Un `n.d.` en una métrica de cabecera no es un detalle
cosmético**: antes de puntuar, mira qué agregados salen vacíos y por qué.

**El aviso de un subagente vale más que su dato.** Los mejores momentos de estas extracciones
no fueron los datos que trajeron, sino los que se negaron a traer: el BPA de 2018 de COP venía
mal desde la SEC (el valor de 2019 duplicado) y el extractor lo detectó con el control de BPA
por acciones, lo reportó y **no lo tocó**; el extractor del balance de COP se negó a repartir
la deuda a corto entre dos cubos cuando la empresa la publica en una sola línea; y otro pilló a
WebFetch devolviéndole como arrendamientos unas cifras que eran los minoritarios. Todo eso
salió de instrucciones explícitas del brief: «si te desvías, NO ajustes, reporta» y «el modelo
pequeño se inventa cifras plausibles». Escríbelas siempre.

**Cuando el companyconcept viene truncado, tira de las páginas R del 10-K.** Los ficheros
`companyconcept` de conceptos muy usados pueden ser enormes, y WebFetch los corta **por el
final**; como los hechos van en orden cronológico ascendente, lo que se pierde es justo lo
reciente. Pasó con la deuda a largo y la caja de Chevron: el corte caía en 2018 y en mediados
de 2024, y quedaron ocho y tres ejercicios vacíos. Pedirlo otra vez igual no sirve, y la API
de `frames` también llegó truncada. Lo que **sí** funcionó: las páginas `R<N>.htm` del informe
financiero de cada 10-K, que son tablas HTML pequeñas con el balance consolidado de dos
ejercicios. Están en `https://www.sec.gov/Archives/edgar/data/<cik>/<accession-sin-guiones>/`
y el índice de cuál es cuál está en el `FilingSummary.xml` del mismo directorio. Con seis
10-K se cubrieron los once valores que faltaban, y cada uno aparece en dos documentos
distintos porque cada balance repite el ejercicio anterior como comparativo: validación cruzada
gratis. Los números de expediente salen del feed
`browse-edgar?action=getcompany&CIK=...&type=10-K&output=atom`, que es XML corto.
**Ojo:** en el intento anterior el modelo pequeño de WebFetch se inventó una lista de números
de expediente con un formato que ni siquiera era el de Chevron. Es la segunda vez hoy. Que una
respuesta llegue redonda no significa que sea cierta: valídala siempre contra algo
independiente antes de escribirla.

**Un dato que no significa lo que el pipeline cree es peor que un dato ausente.** Chevron sí
etiqueta `CostOfGoodsAndServicesSold`, pero ahí solo mete "Purchased crude oil and products",
no un coste de ventas agregado: fuera quedan los gastos de explotación, el agotamiento de
reservas y los impuestos distintos del de sociedades. Dejarlo puesto hacía que `build_src.py`
derivase un margen bruto del 40% que no existe. Se anula, y el margen bruto sale `n.d.`, que
es la verdad. Lo mismo con los ingresos: Chevron presenta dos cifras arriba, ventas y "total
revenues and other income", y la de ventas solo existe desde 2018 porque nace con la ASC 606,
así que la única serie completa de diez ejercicios es la del total; se usa esa **en los diez
años** para no mezclar definiciones dentro de la misma serie, y se dice cuánto cambia (un 4,9%
en FY2024). Las dos operaciones viven en `SERIES_REEMPLAZADAS` de `homogeneiza.py`, que exige
escribir los diez valores y comprueba que la fila actual es la esperada antes de tocar nada.

**Hay emisores que no etiquetan el resultado de explotación.** Chevron no lo hace en ninguno de
los diez ejercicios, e IBM tampoco. Sin él no hay margen operativo, ni EBITDA, ni cobertura de
intereses, ni ROIC. `build_src.py` lo deriva ahora como **EBIT = EBT + gasto financiero**, pero
solo si la fila viene entera a null: si el emisor la publica aunque sea a medias, se respeta lo
publicado. Hay que decir lo que arrastra esa derivación, porque no es neutral: al partir del
resultado antes de impuestos, incluye los ingresos no operativos (resultado de participadas,
plusvalías por venta de activos) y los deterioros. En una petrolera eso no es residual.

**El salto de un split NO está donde ocurrió el split.** Está donde termina la última ventana
comparativa que lo reexpresó, y eso hay que leerlo de la serie, nunca deducirlo de la fecha.
Apple hizo su split 4:1 en agosto de 2020, pero el salto en las acciones diluidas está **entre
FY2017 y FY2018** (5.252 M frente a 20.000 M), porque los 10-K de 2020 y 2021 reexpresaron
FY2018 y FY2019 y la regla del `filed` más reciente los recoge ya divididos; FY2016 y FY2017
se quedaron fuera de toda ventana posterior. En Amazon, split de junio de 2022, el salto está
entre FY2019 y FY2020 por lo mismo. Si hubiera puesto los factores por la fecha del split en
vez de por la serie, en Apple habrían salido mal seis ejercicios y en Amazon tres. **Mira las
acciones diluidas y pon el corte donde esté el salto.** El control de `aplica_split` (BPA x
acciones ≈ beneficio neto) NO lo detecta: es invariante al split, por diseño.

**Un tag vacío puede ser un tag renombrado, no un dato que falte.** En Amazon los cuatro
campos de arrendamientos salían nulos en 2016, 2017 y 2018. La explicación cómoda era la de
siempre — antes de la norma ASC 842 los arrendamientos no se reconocían en balance — y es
verdad, pero **solo para los operativos**. Los financieros sí estaban, con el nombre que
tenían entonces: `CapitalLeaseObligationsCurrent` y `...Noncurrent` en vez de
`FinanceLeaseLiability...`. Darlos por vacíos dejaba fuera **17.370 M$ de deuda en 2018**,
frente a 23.495 M$ de deuda a largo: no era un matiz. Lo mismo pasó con el gasto financiero
de 2024, que había migrado a `InterestExpenseNonoperating`.
En Apple pasó lo mismo con las inversiones a corto de FY2016 y FY2017, que vivían en
`AvailableForSaleSecuritiesCurrent` antes de la ASU 2016-01: sin ellas su caja de esos años
salía de 20.000 M$ en vez de 67.000 y 74.000.
La regla: cuando una fila entera se apaga a partir de un año concreto — o se enciende a partir
de uno —, **antes de aceptar el hueco, busca si la SEC renombró el concepto**. La pista es que el corte coincide con un
cambio de norma contable o con un ejercicio redondo. Rellenarlo no es derivar ni estimar: es
el mismo hecho publicado, y por eso vive en `TAGS_ANTIGUOS` de `homogeneiza.py`, que además
se niega a pisar un valor que ya venga de la SEC.

---

**No toda empresa buena presenta ante la SEC, y no pasa nada: hay que cambiar de fuente,
no rebajar el estándar.** Constellation Software es canadiense (TSX: CSU), presenta en SEDAR+
bajo IFRS y en EDGAR no existe — dos búsquedas por nombre no devolvieron nada. La tentación es
puntuarla con cifras de búsqueda web, y eso está prohibido por la misma razón de siempre. La
salida buena fue ir a sus **cuentas anuales auditadas en PDF**, que son fuente primaria igual
que un 10-K. Cómo se encontraron: el selector de año de su web no dispara por script y adivinar
la URL daba 404, pero la **API REST de WordPress** del sitio las lista todas
(`/wp-json/wp/v2/media?search=Financial-Statement&per_page=40&_fields=source_url,date`).
Dos avisos que costaron tiempo: **WebFetch no sabe leer un PDF, pero lo guarda en disco** y te
dice dónde — ahí es donde empieza el trabajo, no donde termina; y al leerlo con `pypdf` el
estado de flujos sale **con las etiquetas desordenadas al final de la página**, separadas de sus
cifras, así que el mapeo línea-número hay que verificarlo contra las etiquetas que sí salen en
línea antes de citar ningún capex. Con dos PDF (el de 2025 y el de 2023) salieron cuatro
ejercicios completos de los tres estados.

**Cuando la fuente no es la SEC, dilo en la ficha y dilo en el pie.** El dashboard tenía un
texto automático para las candidatas sin ficha: *"su score viene del análisis por búsqueda web,
no de los 10-K de la SEC"*. Para Constellation eso era **falso** y además justo del tipo de
falsedad que importa aquí. Se añadió un campo opcional `fuente` en el objeto de la posición que
sustituye ese texto. Si mañana entra otra empresa por una vía distinta, se usa el mismo campo.

---

## 5 · El entorno: cinco cosas que cuestan tiempo si no se saben

**El push depende del entorno. Compruébalo antes de pedírselo a Maria.**

- **Desde Claude Code en su Mac: `git push` funciona.** El repo tiene
  `credential.helper=osxkeychain` y el token sale del llavero. Comprobado el 6-sep-2026,
  cuatro commits subidos sin intervención suya. **Hazlo tú**: no sabe hacer push a mano y
  pedírselo le carga trabajo que no le toca.
- **Desde el shell del dispositivo: falla** con *could not read Username*, porque no llega
  al llavero. Solo ahí hay que hacer commit en local y pedírselo.

Para saber en cuál estás: `git config --get credential.helper`. Si dice `osxkeychain`,
prueba el push.

Su token necesita **`repo` Y `workflow`**: sin el segundo, cualquier push que toque
`.github/workflows/` se rechaza entero. Ya pasó una vez. `GITHUB.md` lo explica paso a
paso, escrito para ella.

**Lo que sigue sin poder hacerse desde aquí es lanzar un workflow**: `gh` no está
autenticado y la extensión de Chrome no responde, así que Actions → Run workflow lo tiene
que pulsar ella. Se arreglaría con un `gh auth login`.

**Los locks de git.** El shell no puede borrar ficheros por defecto, así que
`.git/HEAD.lock`, `index.lock` y los `tmp_obj_*` sobreviven y bloquean el siguiente push.
Pide `device_request_delete_permission` sobre `~/Claude/Investing` al empezar a tocar git,
y limpia al terminar. El permiso se pierde si el puente se reconecta.

**El proxy bloquea casi todo.** `data.sec.gov`, Yahoo, Stooq, Nasdaq, stockanalysis y los
dominios de noticias devuelven 403 desde el contenedor y desde el dispositivo. La única
vía a la SEC es **WebFetch**, que sí llega y tiene límite de sesión (se agotó dos veces).
Para comprobar cualquier otra fuente hay que ejecutar `probe.yml` en Actions y leer
`probe.json` / `probe_news.json`. **No hay atajo, y esto no es opcional**: el fallo de
precios de la primera sesión se diagnosticó mal hasta que el probe demostró que Yahoo sí
respondía 200 desde Actions y el 429 era por volumen propio.

**Leer PDF en este entorno.** No hay `pdftoppm`, ni librería de PDF en el Python del
sistema, ni `Quartz`. Lo que sí funciona:
`python3 -m pip install --target /tmp/pdflib pypdf` y luego `PYTHONPATH=/tmp/pdflib`. Ojo
también: `timeout` no existe en este zsh.

**Hay cosas que solo se ven ejecutando el Action de verdad.** La primera pasada real
destapó tres fallos que ninguna prueba local habría encontrado: el falso ticker `ROIC`,
que `prices_history.json` se escribía pero el workflow no lo subía, y que Yahoo vuelve a
dar 429 en producción aunque el probe lo diera verde. Después de tocar un script de
Action, mira su ejecución y lee su salida.

**Delegación a subagentes con anclas.** Traer 25 conceptos XBRL al contexto propio no
cabe. Lanza tres subagentes por empresa (resultados, balance, flujo) y dale a cada uno 3-5
valores conocidos que debe reproducir, con la instrucción explícita de que si se desvía
**no ajuste, sino que lo reporte**. Con eso, las seis extracciones de MSFT y META salieron
dentro del 0,1%. Sin anclas, un subagente entrega números plausibles y equivocados sin
darse cuenta. Dos veces el subagente tuvo razón y las anclas estaban mal (activo total y
flujo de explotación de ISRG en 2024): no las forzó, las reportó. Ese es el
comportamiento que hay que pedir.

---

## 6 · Lo que está a medias

Ordenado por lo que más desbloquea.

1. **Lanzar a mano `probe.yml`** (Actions → Run workflow). `news.yml` ya corrió el
   6-sep-2026 y Home se llena: 87 noticias, 15 tickers, 12 de mercado. De la poda que
   quedaba pendiente, hecha la que tenía evidencia y descartada la que no:
   - **`FUENTES_MERCADO` no necesita poda**: sus cinco fuentes responden `ok`. Las "13
     candidatas sin verificar" de la nota anterior no existían; solo hay cinco.
   - **Yahoo retirado de las noticias por ticker**: 429 en los 15, sin aportar ni una
     de las 75 noticias, y costaba unos 135 segundos de reintentos por pasada.
   - **`nasdaq-earnings-date` retirado**: 404 en los 15.
   - **`top_movers()` NO se ha tocado**, y es importante no hacerlo a ciegas: Nasdaq sí
     respondió, con la tabla vacía porque era domingo. Hace falta una pasada en día
     hábil y leer `errors` de `data.json` (que hasta ahora se descartaban).
2. ~~Precios históricos de NVDA~~ — **hecho el 6-sep-2026.** Las seis analizadas ya
   tienen P/E por ejercicio. Lo que hay que saber si se repite para otro ticker con cierre
   fiscal fuera de fin de mes: ver "El periodo mensual miente" en la sección 4.
3. **Inversiones a corto de NVIDIA en FY2026.** No existen bajo ninguno de los tres tags
   habituales; el último hecho es de octubre de 2025. Sin eso, el ROIC y la deuda neta de
   FY2026 salen n.d. Probablemente cambiaron de etiqueta en el 10-K.
4. **Amortización de Microsoft.** Los dos tags estándar dan 404 y el disponible solo cubre
   inmovilizado. Sin eso no hay EBITDA ni Deuda neta/EBITDA de MSFT.
5. **Las 6 posiciones sin analizar con la SEC**: AMZN, AAPL, IBM, COP, WMT, CVX.
6. **Separar el Home por sectores** — pedido por Maria, aplazado explícitamente. La
   referencia es la vista Sectors de Robinhood. El treemap ya está hecho en
   `pintaTreemap()`; falta el mapeo ticker → sector y agrupar por sector.
7. **Toggle inglés / español en las noticias.** Los titulares salen en su idioma de origen.
   Implica guardar una traducción por titular: o traducir en el Action (haría falta un
   servicio con clave) o traducir por lotes en sesión y cachear en `news.json` bajo
   `title_es`.
8. **Precios objetivo de la watchlist.** Sembrados con el extremo bajo del rango de valor
   intrínseco (PGR 180, V 290, PLTR 28, LULU 190, UNP 159, SHEL 69). **Son propuestas de
   Claude, no de Maria.** El de PLTR sale de un DCF puro y no tiene sentido como precio de
   entrada real.
9. **RSI y media de 200** aparecerán solos según se acumule histórico: el RSI a las 15
   sesiones, la media a las 200 (unos diez meses). Hasta entonces salen n.d.
10. **GitHub Pages sin configurar.** Cuando se active, ojo: el repo es público y expone
    participaciones, coste medio y ganancias. Está avisado en `GITHUB.md`.

`TODO.md` lleva la misma lista en casillas.

---

## 7 · Cómo trabaja Maria

Escribe en español. Pidió explícitamente **respuestas directas, sin preámbulos ni
resúmenes, en estilo lacónico**. El 6-sep-2026 tuvo que repetirlo: **bullets cortos, no
párrafos**, porque tanto texto la deja "abrumada y perdida". Es el aviso que más veces se
ha incumplido de todo este documento. El detalle largo va al commit o aquí, no a la
respuesta; si de verdad hace falta extenderse, se pregunta antes. Prefiere ir paso a paso, con las preguntas por delante, y
acepta subagentes que revisen el trabajo.

No es programadora: explícale los pasos de Terminal y de GitHub sin dar nada por supuesto,
y si un comando falla, mira su captura antes de teorizar — la primera vez el error era que
se había perdido la `c` de `cd`.

No le des por buena una conclusión sin el dato detrás. La primera sesión empezó con ella
convencida de que tenía "muchas acciones que no generan ganancia"; los números mostraron
11 de 15 en positivo y que lo que veía en rojo en su app era la línea del último mes, no
el P&L. El valor de este proyecto está en corregir ese tipo de cosas, no en confirmarlas.

Cuando el score y el veredicto no coincidan, dilo: una empresa puede sacar 84 y ser
"Observar" porque el precio no deja margen. Y recuerda que el scoring puntúa empresas de
una en una y **no ve el riesgo de cartera** — el 41,5% está en cuatro compañías atadas al
mismo ciclo de capex de IA, y el capex de GOOGL, MSFT y META (225.689 M$) es prácticamente
la facturación de NVIDIA (215.938 M$). Está en los dos lados del mismo trato.
