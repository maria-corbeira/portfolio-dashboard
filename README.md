# Portfolio Scorecard

Dashboard de seguimiento de cartera con scoring propio (Calidad 40% · Salud 20% ·
Crecimiento 20% · Valoración 15% · Timing 5%) y comparación de precio contra valor
intrínseco estimado.

**Página en vivo:** ver la URL de GitHub Pages en la pestaña *Settings → Pages* del repo.

## Cómo funciona

- `index.html` — el dashboard. Los datos cualitativos (scores, veredictos, valor
  intrínseco, notas) están en los arrays `holdings`, `outsideFramework` y `watchlist`
  al final del archivo. Se editan a mano.
- `scripts/fetch_prices.py` — extrae los tickers de `index.html` y descarga precios
  de Yahoo Finance (con Stooq como respaldo). Escribe `data.json`.
- `.github/workflows/prices.yml` — ejecuta el script cada 15 minutos en horario de
  mercado y hace commit de `data.json` si cambió.
- `data.json` — precios más recientes. El dashboard lo carga al abrirse y lo vuelve
  a pedir cada minuto, así que una pestaña abierta se mantiene al día sola.

## Añadir o quitar un valor

Basta con editar el array correspondiente en `index.html`. El script de precios
detecta los tickers automáticamente, no hay una segunda lista que mantener.

## Refrescar precios a mano

Pestaña **Actions → Actualizar precios → Run workflow**.

## Nota

Los precios tienen hasta ~15 minutos de retraso y proceden de fuentes públicas
gratuitas. No es una fuente de datos de grado profesional ni una recomendación
de inversión.
