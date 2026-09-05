import json, urllib.request, urllib.error, pathlib
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
def get(url, hdrs=None, t=15):
    h={"User-Agent":UA,"Accept":"*/*","Accept-Language":"en-US,en;q=0.9"}
    if hdrs: h.update(hdrs)
    with urllib.request.urlopen(urllib.request.Request(url,headers=h),timeout=t) as r:
        return r.status, r.read()[:600].decode("utf-8","replace")
CANDIDATES = {
 "yahoo_chart":       "https://query1.finance.yahoo.com/v8/finance/chart/MSFT?range=1d&interval=1d",
 "yahoo_spark":       "https://query2.finance.yahoo.com/v7/finance/spark?symbols=MSFT&range=1d&interval=1d",
 "stooq_com":         "https://stooq.com/q/l/?s=msft.us&f=sd2t2ohlcv&h&e=csv",
 "stooq_pl":          "https://stooq.pl/q/l/?s=msft.us&f=sd2t2ohlcv&h&e=csv",
 "cnbc":              "https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol?symbols=MSFT&requestMethod=itv&noform=1&partnerId=2&fund=1&exthrs=1&output=json",
 "nasdaq":            "https://api.nasdaq.com/api/quote/MSFT/info?assetclass=stocks",
 "wsj":               "https://www.wsj.com/market-data/quotes/MSFT",
 "fmp_demo":          "https://financialmodelingprep.com/api/v3/quote-short/AAPL?apikey=demo",
 "twelvedata_demo":   "https://api.twelvedata.com/price?symbol=MSFT&apikey=demo",
 "alphavantage_demo": "https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=IBM&apikey=demo",
 "coincap_style_hn":  "https://api.marketdata.app/v1/stocks/quotes/MSFT/",
}
res={}
for name,url in CANDIDATES.items():
    try:
        st,body=get(url)
        res[name]={"status":st,"body":body[:400]}
    except urllib.error.HTTPError as e:
        res[name]={"status":e.code,"body":str(e)[:200]}
    except Exception as e:
        res[name]={"status":"ERR","body":f"{type(e).__name__}: {str(e)[:200]}"}
    print(name, res[name]["status"])
pathlib.Path(__file__).resolve().parent.parent.joinpath("probe.json").write_text(
    json.dumps(res,indent=2,ensure_ascii=False), encoding="utf-8")
