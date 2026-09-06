#!/usr/bin/env python3
"""
Descarga precios de mercado para todos los tickers que aparecen en index.html
y los guarda en data.json. Lo ejecuta el GitHub Action .github/workflows/prices.yml.

No hay que mantener ninguna lista aqui: los tickers se extraen del propio
index.html (los campos t:"XXX" de holdings, outsideFramework y watchlist).

Estrategia (probada contra las IPs de GitHub Actions, ver probe.json):
  1. Yahoo /v7/finance/spark  -> UNA sola peticion para todos los tickers.
     El fallo anterior (HTTP 429) venia de hacer 22x2 peticiones seguidas.
  2. CNBC quote API           -> tambien por lotes, sin API key.
  3. Nasdaq API               -> por ticker, para los que sigan faltando.
  4. Yahoo /v8/finance/chart  -> por ticker, ultimo recurso.
Cada fuente reintenta con espera creciente ante 429/503.
"""
import json, re, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import history as H

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
OUT = ROOT / "data.json"
HIST = ROOT / "prices_history.json"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
BATCH = 20          # tickers por peticion
RETRIES = 3

ERRORS: list[str] = []


def log_err(tag: str, e: Exception) -> None:
    ERRORS.append(f"{tag}: {type(e).__name__}: {str(e)[:160]}")


def tickers_from_index() -> list[str]:
    """Solo se miran los tres arrays de posiciones. Barriendo el fichero entero
    se colaba cualquier otra clave en mayusculas del resto del codigo."""
    html = INDEX.read_text(encoding="utf-8")
    ini, fin = html.index("const holdings"), html.index("const verdictLabel")
    found = re.findall(r'\bt:\s*"([A-Z][A-Z0-9.\-]{0,9})"', html[ini:fin])
    seen, out = set(), []
    for t in found:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _get(url: str, timeout: int = 25, tag: str = "") -> bytes | None:
    """GET con reintentos ante 429/503."""
    for attempt in range(RETRIES):
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Accept": "application/json,text/plain,*/*",
            "Accept-Language": "en-US,en;q=0.9",
        })
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < RETRIES - 1:
                time.sleep(2 ** attempt * 3)   # 3s, 6s
                continue
            log_err(f"{tag}", e)
            return None
        except Exception as e:
            if attempt < RETRIES - 1:
                time.sleep(2)
                continue
            log_err(f"{tag}", e)
            return None
    return None


def _quote(price, prev, currency="USD", mtime=None, source="") -> dict | None:
    try:
        price = float(price)
    except (TypeError, ValueError):
        return None
    try:
        prev = float(prev)
    except (TypeError, ValueError):
        prev = None
    return {
        "price": round(price, 2),
        "prev_close": round(prev, 2) if prev else None,
        "change_pct": round((price / prev - 1) * 100, 2) if prev else None,
        "currency": currency,
        "market_time": mtime,
        "source": source,
    }


# ---------------------------------------------------------------- fuentes ---

def yahoo_spark(tickers: list[str]) -> dict:
    """Una peticion para hasta BATCH tickers. Fuente principal."""
    out = {}
    for i in range(0, len(tickers), BATCH):
        chunk = tickers[i:i + BATCH]
        url = ("https://query1.finance.yahoo.com/v7/finance/spark"
               f"?symbols={','.join(chunk)}&range=5d&interval=1d")
        raw = _get(url, tag=f"yahoo_spark[{chunk[0]}...]")
        if not raw:
            continue
        try:
            results = json.loads(raw)["spark"]["result"]
        except Exception as e:
            log_err("yahoo_spark parse", e)
            continue
        for r in results:
            try:
                meta = r["response"][0]["meta"]
            except Exception:
                continue
            q = _quote(meta.get("regularMarketPrice"),
                       meta.get("chartPreviousClose") or meta.get("previousClose"),
                       meta.get("currency", "USD"),
                       meta.get("regularMarketTime"),
                       "yahoo_spark")
            if q:
                out[r.get("symbol", meta.get("symbol"))] = q
        time.sleep(1)
    return out


def cnbc_batch(tickers: list[str]) -> dict:
    """CNBC acepta varios simbolos separados por '|'. Sin API key."""
    out = {}
    for i in range(0, len(tickers), BATCH):
        chunk = tickers[i:i + BATCH]
        url = ("https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol"
               f"?symbols={'%7C'.join(chunk)}&requestMethod=itv&noform=1"
               "&partnerId=2&fund=1&exthrs=0&output=json")
        raw = _get(url, tag=f"cnbc[{chunk[0]}...]")
        if not raw:
            continue
        try:
            data = json.loads(raw)["FormattedQuoteResult"]["FormattedQuote"]
        except Exception as e:
            log_err("cnbc parse", e)
            continue
        if isinstance(data, dict):
            data = [data]
        for row in data:
            sym = row.get("symbol")
            last = str(row.get("last", "")).replace(",", "").replace("$", "")
            prev = str(row.get("previous_day_closing", "")).replace(",", "").replace("$", "")
            q = _quote(last, prev, row.get("currencyCode") or "USD", None, "cnbc")
            if sym and q:
                out[sym] = q
        time.sleep(1)
    return out


def nasdaq_one(ticker: str) -> dict | None:
    for cls in ("stocks", "etf"):
        url = f"https://api.nasdaq.com/api/quote/{ticker}/info?assetclass={cls}"
        raw = _get(url, tag=f"nasdaq/{cls} {ticker}")
        if not raw:
            continue
        try:
            d = json.loads(raw).get("data") or {}
            pd = d.get("primaryData") or {}
            last = str(pd.get("lastSalePrice", "")).replace("$", "").replace(",", "")
            net = str(pd.get("netChange", "")).replace(",", "")
            price = float(last)
            prev = price - float(net) if net not in ("", "N/A", "UNCH") else None
            q = _quote(price, prev, "USD", None, "nasdaq")
            if q:
                return q
        except Exception as e:
            log_err(f"nasdaq/{cls} {ticker} parse", e)
    return None


def yahoo_chart_one(ticker: str) -> dict | None:
    for host in ("query1", "query2"):
        url = (f"https://{host}.finance.yahoo.com/v8/finance/chart/{ticker}"
               "?range=5d&interval=1d&includePrePost=false")
        raw = _get(url, tag=f"yahoo_chart/{host} {ticker}")
        if not raw:
            continue
        try:
            meta = json.loads(raw)["chart"]["result"][0]["meta"]
        except Exception as e:
            log_err(f"yahoo_chart {ticker} parse", e)
            continue
        q = _quote(meta.get("regularMarketPrice"),
                   meta.get("chartPreviousClose") or meta.get("previousClose"),
                   meta.get("currency", "USD"),
                   meta.get("regularMarketTime"),
                   "yahoo_chart")
        if q:
            return q
    return None


def top_movers():
    """Mayores subidas y bajadas del mercado. No hay una fuente publica gratuita
    de referencia, asi que se prueban tres en cascada y se registra cual respondio.
    Si ninguna responde, devuelve vacio: no se estiman movimientos."""
    candidatas = [
        ("nasdaq_marketmovers",
         "https://api.nasdaq.com/api/marketmovers",
         lambda d: [(r.get("symbol"), r.get("pctchange"), grupo)
                    for grupo, clave in (("subidas", "GAINERS"), ("bajadas", "LOSERS"))
                    for r in (((d.get("data") or {}).get(clave) or {}).get("table") or {}).get("rows", [])]),
        ("yahoo_day_gainers",
         "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved"
         "?scrIds=day_gainers&count=8",
         lambda d: [(q.get("symbol"), q.get("regularMarketChangePercent"), "subidas")
                    for q in (((d.get("finance") or {}).get("result") or [{}])[0]
                              .get("quotes") or [])]),
        ("yahoo_day_losers",
         "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved"
         "?scrIds=day_losers&count=8",
         lambda d: [(q.get("symbol"), q.get("regularMarketChangePercent"), "bajadas")
                    for q in (((d.get("finance") or {}).get("result") or [{}])[0]
                              .get("quotes") or [])]),
    ]
    filas, usadas = [], []
    for nombre, url, extrae in candidatas:
        raw = _get(url, tag=f"movers/{nombre}")
        if not raw:
            continue
        try:
            for sym, pct, grupo in extrae(json.loads(raw)):
                if not sym or pct in (None, ""):
                    continue
                try:
                    v = float(str(pct).replace("%", "").replace("+", "").replace(",", ""))
                except ValueError:
                    continue
                filas.append({"ticker": sym, "pct": round(v, 2), "grupo": grupo,
                              "fuente": nombre})
            usadas.append(nombre)
        except Exception as e:
            ERRORS.append(f"movers/{nombre} parse: {type(e).__name__}: {str(e)[:100]}")
        if filas:
            break
    vistos, out = set(), []
    for f in sorted(filas, key=lambda x: abs(x["pct"]), reverse=True):
        if f["ticker"] in vistos:
            continue
        vistos.add(f["ticker"])
        out.append(f)
    return out[:10], usadas


# ------------------------------------------------------------------ main ---

def main() -> int:
    tickers = tickers_from_index()
    if not tickers:
        print("ERROR: no se encontro ningun ticker en index.html", file=sys.stderr)
        return 1
    print(f"{len(tickers)} tickers: {', '.join(tickers)}")

    prices: dict[str, dict] = {}

    for name, fn in (("yahoo_spark", yahoo_spark), ("cnbc", cnbc_batch)):
        missing = [t for t in tickers if t not in prices]
        if not missing:
            break
        got = fn(missing)
        prices.update({k: v for k, v in got.items() if k in missing})
        print(f"  {name}: {len(got)} ok, faltan {len([t for t in tickers if t not in prices])}")

    for t in [t for t in tickers if t not in prices]:
        q = nasdaq_one(t) or yahoo_chart_one(t)
        if q:
            prices[t] = q
            print(f"  rescate {t} via {q['source']}")
        time.sleep(0.5)

    failed = [t for t in tickers if t not in prices]
    for t in sorted(prices):
        q = prices[t]
        chg = f"({q['change_pct']:+.2f}%)" if q["change_pct"] is not None else ""
        print(f"  {t:<6} {q['price']:>9.2f}  {chg:<10} [{q['source']}]")

    # Historico: un punto por sesion y ticker. De ahi salen las variaciones a 1 y
    # 5 sesiones, el RSI de 14 y la media de 200, que antes no se podian calcular.
    series = H.carga(HIST)
    if prices:
        series = H.actualiza(series, prices)
        H.guarda(HIST, series)
    indic = H.indicadores(series, prices)
    movimientos = H.fuertes(indic)
    movers, movers_fuente = top_movers()

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "count": len(prices),
        "failed": failed,
        "prices": prices,
        "indicadores": indic,
        "movimientos_fuertes": movimientos,
        "umbral_fuerte": H.UMBRAL_FUERTE,
        "top_movers": movers,
        "top_movers_fuente": movers_fuente,
    }
    if failed:
        payload["errors"] = ERRORS[:20]

    # Nunca sobrescribir datos buenos con un fichero vacio.
    if not prices and OUT.exists():
        try:
            prev = json.loads(OUT.read_text(encoding="utf-8"))
            if prev.get("count"):
                print("Sin datos nuevos; se conserva el data.json anterior.", file=sys.stderr)
                for e in ERRORS[:20]:
                    print("  !", e)
                return 1
        except Exception:
            pass

    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    con_rsi = sum(1 for d in indic.values() if d["rsi_14"] is not None)
    con_ma = sum(1 for d in indic.values() if d["ma_200"] is not None)
    print(f"\nhistorico: {len(series)} tickers · RSI en {con_rsi} · media de 200 en {con_ma}")
    if movimientos:
        print("movimientos fuertes:")
        for m in movimientos:
            print(f"  {m['ticker']:<6} {m['pct']:+.2f}% en {m['ventana']}")
    print(f"\ndata.json escrito: {len(prices)} ok, {len(failed)} fallidos")
    for e in ERRORS[:20]:
        print("  !", e)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
