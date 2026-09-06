#!/usr/bin/env python3
"""Comprueba, desde las IPs de GitHub Actions, que fuentes de noticias responden.
Se ejecuta con .github/workflows/probe.yml y deja el resultado en probe_news.json.
Desde la sesion de Claude no se pueden probar: el proxy de egress las bloquea."""
import json, urllib.request, urllib.error, pathlib
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
CANDIDATAS = {
 "yahoo_ticker":   "https://feeds.finance.yahoo.com/rss/2.0/headline?s=NVDA&region=US&lang=en-US",
 "google_ticker":  "https://news.google.com/rss/search?q=NVDA+stock+when:30d&hl=en-US&gl=US&ceid=US:en",
 "google_mercado": "https://news.google.com/rss/search?q=stock+market+when:3d&hl=en-US&gl=US&ceid=US:en",
 "marketwatch":    "https://feeds.content.dowjones.io/public/rss/mw_topstories",
 "cnbc_mercados":  "https://search.cnbc.com/rs/search/combinedcderpage.htm?partnerId=wrss01&id=20910258",
 "fed_prensa":     "https://www.federalreserve.gov/feeds/press_all.xml",
 "nasdaq_earndate":"https://api.nasdaq.com/api/company/NVDA/earnings-date",
 "nasdaq_eps":     "https://api.nasdaq.com/api/quote/NVDA/eps",
 "nasdaq_calend":  "https://api.nasdaq.com/api/calendar/earnings?date=2026-09-08",
 "nasdaq_movers":  "https://api.nasdaq.com/api/marketmovers",
 "yahoo_gainers":  "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved?scrIds=day_gainers&count=8",
 "yahoo_losers":   "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved?scrIds=day_losers&count=8",
 "sec_8k":         "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001045810&type=8-K&count=5&output=atom",
}
res = {}
for nombre, url in CANDIDATAS.items():
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
        with urllib.request.urlopen(req, timeout=20) as r:
            cuerpo = r.read()
            res[nombre] = {"status": r.status, "bytes": len(cuerpo),
                           "items": cuerpo.count(b"<item"),
                           "muestra": cuerpo[:300].decode("utf-8", "replace")}
    except urllib.error.HTTPError as e:
        res[nombre] = {"status": e.code, "bytes": 0, "items": 0, "muestra": str(e)[:200]}
    except Exception as e:
        res[nombre] = {"status": "ERR", "bytes": 0, "items": 0,
                       "muestra": f"{type(e).__name__}: {str(e)[:200]}"}
    print(nombre, res[nombre]["status"], res[nombre]["items"], "items")
pathlib.Path(__file__).resolve().parent.parent.joinpath("probe_news.json").write_text(
    json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
