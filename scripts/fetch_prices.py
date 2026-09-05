#!/usr/bin/env python3
"""
Descarga precios de mercado para todos los tickers que aparecen en index.html
y los guarda en data.json. Lo ejecuta el GitHub Action .github/workflows/prices.yml.

No hay que mantener ninguna lista aquí: los tickers se extraen del propio
index.html (los campos t:"XXX" de holdings, outsideFramework y watchlist).
"""
import json, re, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
OUT = ROOT / "data.json"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"


def tickers_from_index() -> list[str]:
    html = INDEX.read_text(encoding="utf-8")
    found = re.findall(r'\bt:\s*"([A-Z][A-Z0-9.\-]{0,9})"', html)
    seen, out = set(), []
    for t in found:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _get(url: str, timeout: int = 20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


ERRORS: list[str] = []


def from_yahoo(ticker: str):
    """Precio actual + cierre anterior desde el chart API de Yahoo Finance."""
    for host in ("query1", "query2"):
        url = (f"https://{host}.finance.yahoo.com/v8/finance/chart/{ticker}"
               f"?range=5d&interval=1d&includePrePost=false")
        try:
            meta = json.loads(_get(url))["chart"]["result"][0]["meta"]
        except Exception as e:
            ERRORS.append(f"yahoo/{host} {ticker}: {type(e).__name__}: {str(e)[:160]}")
            continue
        price = meta.get("regularMarketPrice")
        prev = meta.get("chartPreviousClose") or meta.get("previousClose")
        if price is None:
            continue
        return {
            "price": round(float(price), 2),
            "prev_close": round(float(prev), 2) if prev else None,
            "change_pct": round((float(price) / float(prev) - 1) * 100, 2) if prev else None,
            "currency": meta.get("currency"),
            "market_time": meta.get("regularMarketTime"),
            "source": "yahoo",
        }
    return None


def from_stooq(ticker: str):
    """Fallback: CSV de stooq.com (cierre del día anterior, sin intradía)."""
    url = f"https://stooq.com/q/l/?s={ticker.lower()}.us&f=sd2t2ohlcv&h&e=csv"
    try:
        rows = _get(url).decode().strip().splitlines()
        if len(rows) < 2:
            return None
        cols = dict(zip(rows[0].split(","), rows[1].split(",")))
        close, open_ = float(cols["Close"]), float(cols["Open"])
        return {
            "price": round(close, 2),
            "prev_close": round(open_, 2),
            "change_pct": round((close / open_ - 1) * 100, 2) if open_ else None,
            "currency": "USD",
            "market_time": None,
            "source": "stooq",
        }
    except Exception as e:
        ERRORS.append(f"stooq {ticker}: {type(e).__name__}: {str(e)[:160]}")
        return None


def main() -> int:
    tickers = tickers_from_index()
    if not tickers:
        print("ERROR: no se encontró ningún ticker en index.html", file=sys.stderr)
        return 1
    print(f"{len(tickers)} tickers: {', '.join(tickers)}")

    prices, failed = {}, []
    for t in tickers:
        q = from_yahoo(t) or from_stooq(t)
        if q:
            prices[t] = q
            print(f"  {t:<6} {q['price']:>9.2f}  ({q['change_pct']:+.2f}%)" if q["change_pct"] is not None
                  else f"  {t:<6} {q['price']:>9.2f}")
        else:
            failed.append(t)
            print(f"  {t:<6} SIN DATOS")
        time.sleep(0.25)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "count": len(prices),
        "failed": failed,
        "prices": prices,
    }
    if not prices:
        # Se escribe igualmente para dejar rastro de por qué falló.
        payload["errors"] = ERRORS[:12]
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\ndata.json escrito: {len(prices)} ok, {len(failed)} fallidos")
    for e in ERRORS[:12]:
        print("  !", e)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
