# Hand-off — dashboard de cartera de Maria

Para el agente que continúe. **Léelo entero antes de tocar nada.** Contiene errores
ya cometidos y resueltos: repetirlos cuesta horas.

Escrito el 6-sep-2026 al pasar la conversación a Claude Code.

---

## 1 · Qué es esto

Un dashboard de cartera en un solo `index.html`, publicado en GitHub Pages desde
`github.com/maria-corbeira/portfolio-dashboard`. Dos GitHub Actions lo alimentan
con precios y noticias. Maria decide con él si mantener, ampliar o vender.

**No es un juguete: se toman decisiones de inversión con estos números.** La regla
que gobierna todo el proyecto es que un dato que no se ha podido obtener sale como
`n.d.` y se dice por qué. Nunca se rellena con una estimación, una media ni un cero.

### Estado a 6-sep-2026

- 15 posiciones reales, 6 candidatas en watchlist.
- **6 empresas analizadas con 10 años de datos de la SEC**: GOOGL, MSFT, META, UBER,
  ISRG, NVDA. Las otras 6 (AMZN, AAPL, IBM, COP, WMT, CVX) siguen con scores de
  búsqueda web de la primera sesión — están marcadas como tales en su ficha.
- **Hay 9 commits sin subir.** Maria tiene que hacer `git push` (ver §6). Hasta que
  no lo haga, los Actions no existen en GitHub y no hay ni precios ni noticias.

---

## 2 · Las tres skills

Están guardadas en la cuenta de Maria y son la forma correcta de trabajar:

| Skill | Para qué |
|---|---|
| `analisis-value-quality` | El framework de scoring 0-100 y el formato de respuesta |
| `datos-sec-10anios` | Extraer 10 años de estados financieros de la SEC |
| `dashboard-cartera` | Mantener este repo |

Úsalas. Recogen decisiones que costaron toda una sesión.

---

## 3 · Arquitectura

```
index.html            TODO el dashboard: datos, estilos y lógica en un fichero
  holdings[]          15 posiciones (12 acciones + los 3 ETF van en outsideFramework)
  outsideFramework[]  QQQ, VOO, IAUM
  watchlist[]         6 candidatas, con `target` = precio de entrada objetivo
  const fundamentals  incrustado entre // <<<FUNDAMENTALS y // FUNDAMENTALS>>>
  3 paneles           #tab-home · #tab-stocks · #tab-watch

data.json             precios + indicadores + movimientos fuertes + top movers
prices_history.json   cierre diario por ticker, 420 sesiones
news.json             noticias por ticker y de mercado, calendario de resultados
eventos.json          keynotes y presentaciones, CURADO A MANO
fundamentals/
  raw/                las extracciones de la SEC con sus tags y avisos
  raw/_precios.json   cierres por ejercicio, para el P/E histórico
  <T>.src.json        10 ejercicios en formato plantilla IDC
  <T>.json            métricas calculadas
scripts/
  fetch_prices.py     precios; lo ejecuta prices.yml cada 15 min
  history.py          histórico, variaciones, RSI de 14, media de 200
  fetch_news.py       noticias; lo ejecuta news.yml cada 6 h
  load_raw.py         vuelca las extracciones de GOOGL/MSFT/META
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

**Un vacío no es un cero.** Costó un fallo real: `metrics.py` trataba una caja vacía
como cero al calcular el capital invertido y hundía el ROIC de Microsoft en FY2016-17
(16,6% en vez de ~50%). Si falta un componente, propaga el vacío.

**Verifica cada sustitución de texto.** Editar `index.html` con `str.replace` sin
comprobar el número de coincidencias hace que un cambio se pierda en silencio. Pasó:
dos `replace` se perdieron porque un `assert` posterior abortó el script antes de
escribir. Usa siempre este patrón:

```python
def sust(s, viejo, nuevo, etiqueta):
    n = s.count(viejo)
    assert n == 1, f"{etiqueta}: {n} coincidencias, se esperaba 1"
    return s.replace(viejo, nuevo, 1)
```

**Comprueba el JS y RENDERIZA antes de dar nada por bueno.**

```bash
python3 -c "s=open('index.html',encoding='utf-8').read(); a=s.index('<script>')+8; b=s.rindex('</script>'); open('/tmp/app.js','w').write(s[a:b])"
node --check /tmp/app.js
```

Un error habitual al reemplazar una línea de un array es **comerse la coma final**, y
el fallo aparece señalando la línea siguiente. Después levanta un servidor y abre la
página con Playwright (`chromium` preinstalado, `PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers`),
captura `pageerror`, despliega filas y **comprueba las cifras contra un cálculo aparte**.
Con `file://` la carga de los JSON falla por CORS: usa `http.server`.

Tres errores llegaron hasta la captura de pantalla y solo se vieron ahí: un `$`
perdido, un `"% pp"` duplicado y un treemap que codificaba el área al revés.

**Los gráficos codifican, no decoran.** El área del treemap es el peso real de la
posición (desvío máximo medido: 0,4 puntos). Los huecos se dibujan como huecos: NVIDIA
no tiene FCF antes de FY2022 y la línea se corta en vez de interpolar. Si el último
valor de una serie no es el del ejercicio más reciente, se etiqueta con su año.

**Color: nunca la única señal.** El verde puro contra el rojo falla la validación de
daltonismo (ΔE 4,6 en deuteranopía, indistinguibles). Se usa el aqua de la paleta
validada y cada casilla lleva siempre el número con signo. Para validar una paleta
nueva, usa la skill `dataviz` y su `scripts/validate_palette.js`. **No lo estimes a
ojo, ejecútalo.**

---

## 5 · El entorno: cuatro cosas que cuestan tiempo si no se saben

**El push lo tiene que hacer Maria.** El shell del dispositivo no llega al llavero de
macOS: `git push` falla con *could not read Username*. `pull` y `fetch` sí funcionan.
Haz commit en local y pídeselo.

**Los locks de git.** El shell no puede borrar ficheros por defecto, así que
`.git/HEAD.lock`, `index.lock` y los `tmp_obj_*` sobreviven y bloquean el siguiente
push. Pide `device_request_delete_permission` sobre `~/Claude/Investing` al empezar a
tocar git, y limpia al terminar. El permiso se pierde si el puente se reconecta.

**El proxy bloquea casi todo.** `data.sec.gov`, Yahoo, Stooq, Nasdaq y los dominios de
noticias devuelven 403 desde el contenedor y desde el dispositivo. La única vía a la
SEC es **WebFetch**, que sí llega y tiene límite de sesión (se agotó dos veces). Para
comprobar cualquier otra fuente hay que ejecutar `probe.yml` en GitHub Actions y leer
`probe.json` / `probe_news.json`. **No hay atajo.**

**Delegación a subagentes con anclas.** Traer 25 conceptos XBRL al contexto propio no
cabe. Lanza tres subagentes por empresa (resultados, balance, flujo) y dale a cada uno
3-5 valores conocidos que debe reproducir, con la instrucción explícita de que si se
desvía **no ajuste, sino que lo reporte**. Con eso, las seis extracciones de MSFT y
META salieron dentro del 0,1%. Sin anclas, un subagente entrega números plausibles y
equivocados sin darse cuenta.

Dos veces el subagente tuvo razón y mis anclas estaban mal (activo total y flujo de
explotación de ISRG en 2024). No las forzó, las reportó. Ese es el comportamiento que
hay que pedir.

---

## 6 · Lo que está a medias

Ordenado por lo que más desbloquea.

1. **`git push` de los 9 commits.** Bloquea absolutamente todo lo demás.
2. **Ejecutar `probe.yml`** y podar fuentes según `probe_news.json`. Hay 13 candidatas
   sin verificar: noticias, calendario de resultados y las tres de top movers.
3. **Precios históricos de NVDA** — es lo único que falta para tener el P/E por
   ejercicio de las seis. Una consulta a
   `https://stockanalysis.com/api/symbol/s/nvda/history?range=10Y&period=Monthly`,
   tomando la fila de enero (NVIDIA cierra el último domingo de enero).
4. **Inversiones a corto de NVIDIA en FY2026.** No existen bajo ninguno de los tres
   tags habituales; el último hecho es de octubre de 2025. Sin eso, el ROIC y la deuda
   neta de FY2026 salen n.d. Probablemente cambiaron de etiqueta en el 10-K.
5. **Amortización de Microsoft.** Los dos tags estándar dan 404 y el disponible solo
   cubre inmovilizado. Sin eso no hay EBITDA ni Deuda neta/EBITDA de MSFT.
6. **Las 6 posiciones sin analizar con la SEC**: AMZN, AAPL, IBM, COP, WMT, CVX.
7. **Separar el Home por sectores** — pedido por Maria, aplazado. La referencia es la
   vista de Sectors de Robinhood: un treemap por sector. El treemap ya está hecho en
   `pintaTreemap()`; falta el mapeo ticker -> sector y agrupar.
8. **Toggle inglés / español en las noticias.** Los titulares salen en su idioma de
   origen. Implica guardar una traducción por titular: o traducir en el Action (haría
   falta un servicio con clave) o traducir por lotes en sesión y cachear en `news.json`
   bajo `title_es`.
9. **Precios objetivo de la watchlist.** Los sembré con el extremo bajo del rango de
   valor intrínseco (PGR 180, V 290, PLTR 28, LULU 190, UNP 159, SHEL 69). **Son
   propuestas mías, no de Maria.** El de PLTR sale de un DCF puro y no tiene sentido
   como precio de entrada real.
10. **RSI y media de 200** aparecerán solos según se acumule histórico: el RSI a las 15
    sesiones, la media a las 200 (unos diez meses). Hasta entonces salen n.d.

`TODO.md` lleva la misma lista en formato de casillas.

---

## 7 · Cómo trabaja Maria

Escribe en español. Pidió explícitamente **respuestas directas, sin preámbulos ni
resúmenes, en estilo lacónico**. Prefiere ir paso a paso, con las preguntas por
delante, y acepta subagentes que revisen el trabajo.

No le des por buena una conclusión sin el dato detrás. La primera sesión empezó con
ella convencida de que tenía "muchas acciones que no generan ganancia"; los números
mostraron 11 de 15 en positivo y que lo que veía en rojo en su app era la línea del
último mes, no el P&L. El valor de este proyecto está en corregir ese tipo de cosas,
no en confirmarlas.

Cuando el score y el veredicto no coincidan, dilo: una empresa puede sacar 84 y ser
"Observar" porque el precio no deja margen. Y recuerda que el scoring puntúa empresas
de una en una y **no ve el riesgo de cartera** — el 41,5% está en cuatro compañías
atadas al mismo ciclo de capex de IA, y el capex de GOOGL, MSFT y META (225.689 M$) es
prácticamente la facturación de NVIDIA (215.938 M$). Está en los dos lados del mismo
trato.
