#!/usr/bin/env python3
"""
Motor de metricas del scoring value+quality.

Entrada : un JSON en formato plantilla IDC (el que produce el plugin
          valoracion-idc): {"ticker", "fiscal_dates", "sheets": {...}}
Salida  : un JSON con las metricas por ejercicio + agregados, listo para el
          dashboard. NO inventa nada: lo que no se puede calcular sale null.

Uso: python3 scripts/metrics.py ruta/al/full_TICKER.json [-o salida.json]
"""
import json, sys, argparse
from pathlib import Path

IS, BS, CF, VAL = "7.TIKR_IS", "8.TIKR_BS", "9.TIKR_CF", "10.TIKR_Val"


def get(d, sheet, row):
    return (d["sheets"].get(sheet) or {}).get(row)


def div(a, b):
    """Division segura. None si falta un dato o el denominador no es utilizable."""
    if a is None or b in (None, 0):
        return None
    try:
        return a / b
    except (TypeError, ZeroDivisionError):
        return None


def pct(x, nd=1):
    return None if x is None else round(x * 100, nd)


def cagr(series, years):
    """CAGR sobre los ultimos `years` periodos. None si hay signo negativo."""
    if len(series) < years + 1:
        return None
    a, b = series[-years - 1], series[-1]
    if a is None or b is None or a <= 0 or b <= 0:
        return None
    return (b / a) ** (1 / years) - 1


def yoy(series):
    out = [None]
    for prev, cur in zip(series, series[1:]):
        out.append(None if (prev in (None, 0) or cur is None) else cur / prev - 1)
    return out


def compute(d):
    dates = d["fiscal_dates"]
    n = len(dates)
    z = lambda x: (x or [None] * n)

    rev      = z(get(d, IS, "Total Revenues"))
    cogs     = z(get(d, IS, "Cost of Goods Sold"))
    gross    = z(get(d, IS, "Gross Profit"))
    opinc    = z(get(d, IS, "Operating Income"))
    ebitda   = z(get(d, IS, "EBITDA"))
    intexp   = z(get(d, IS, "Interest Expense"))
    tax      = z(get(d, IS, "Income Tax Expense"))
    ebt      = z(get(d, IS, "EBT Incl. Unusual Items"))
    ni       = z(get(d, IS, "Net Income"))
    eps      = z(get(d, IS, "Diluted EPS Excl Extra Items"))
    dilsh    = z(get(d, IS, "Weighted Average Diluted Shares Outstanding"))

    tca      = z(get(d, BS, "Total Current Assets"))
    tcl      = z(get(d, BS, "Total Current Liabilities"))
    assets   = z(get(d, BS, "Total Assets"))
    equity   = z(get(d, BS, "Total Equity"))
    debt     = z(get(d, BS, "Total Debt"))
    netdebt  = z(get(d, BS, "Net Debt"))
    cash     = z(get(d, BS, "Total Cash And Short Term Investments"))

    cfo      = z(get(d, CF, "Cash from Operations"))
    capex    = z(get(d, CF, "Capital Expenditure"))
    fcf      = z(get(d, CF, "Free Cash Flow"))
    sbc      = z(get(d, CF, "Stock-Based Compensation"))
    buyback  = z(get(d, CF, "Repurchase of Common Stock"))

    mcap     = z(get(d, VAL, "Market Cap (MM)"))
    price    = z(get(d, VAL, "Price")) or z(get(d, IS, "Price Close"))

    # FCF de respaldo si la fila no viene: CFO + capex (capex ya es negativo)
    fcf = [f if f is not None else (None if (c is None or x is None) else c + x)
           for f, c, x in zip(fcf, cfo, capex)]

    rows = []
    for i in range(n):
        # tasa impositiva efectiva: Income Tax Expense viene negativo
        etr = None
        if ebt[i] not in (None, 0) and tax[i] is not None:
            etr = abs(tax[i]) / ebt[i] if ebt[i] > 0 else None
            if etr is not None and not (0 <= etr <= 0.6):
                etr = None
        nopat = None if (opinc[i] is None or etr is None) else opinc[i] * (1 - etr)
        # capital invertido = deuda total + fondos propios - caja y equivalentes
        ic = None
        if debt[i] is not None and equity[i] is not None:
            ic = debt[i] + equity[i] - (cash[i] or 0)
            if ic <= 0:
                ic = None

        rows.append({
            "year": dates[i][:4],
            "revenue": rev[i],
            "gross_margin": pct(div(gross[i], rev[i])),
            "operating_margin": pct(div(opinc[i], rev[i])),
            "net_margin": pct(div(ni[i], rev[i])),
            "roe": pct(div(ni[i], equity[i])),
            "roa": pct(div(ni[i], assets[i])),
            "roic": pct(div(nopat, ic)),
            "effective_tax_rate": pct(etr),
            "interest_coverage": (None if intexp[i] in (None, 0)
                                  else round(div(opinc[i], abs(intexp[i])) or 0, 1)
                                  if opinc[i] is not None else None),
            "debt_to_equity": None if div(debt[i], equity[i]) is None else round(div(debt[i], equity[i]), 2),
            "net_debt_ebitda": None if div(netdebt[i], ebitda[i]) is None else round(div(netdebt[i], ebitda[i]), 2),
            "current_ratio": None if div(tca[i], tcl[i]) is None else round(div(tca[i], tcl[i]), 2),
            "eps_diluted": eps[i],
            "diluted_shares": dilsh[i],
            "cfo": cfo[i],
            "capex": capex[i],
            "fcf": fcf[i],
            "fcf_margin": pct(div(fcf[i], rev[i])),
            "sbc_pct_revenue": pct(div(sbc[i], rev[i])),
            "buyback": buyback[i],
            "market_cap": mcap[i],
            "price_close": price[i],
            "pe": None if div(mcap[i], ni[i]) is None else round(div(mcap[i], ni[i]), 1),
            "fcf_yield": pct(div(fcf[i], mcap[i]), 2),
        })

    rev_g, eps_g, fcf_g = yoy(rev), yoy(eps), yoy(fcf)
    for i, r in enumerate(rows):
        r["revenue_growth"] = pct(rev_g[i])
        r["eps_growth"] = pct(eps_g[i])
        r["fcf_growth"] = pct(fcf_g[i])

    def last(key):
        return rows[-1][key] if rows else None

    agg = {
        "years_covered": f"{dates[0][:4]}-{dates[-1][:4]}",
        "revenue_cagr_5y": pct(cagr(rev, 5)),
        "revenue_cagr_10y": pct(cagr(rev, min(10, n - 1))),
        "eps_cagr_5y": pct(cagr(eps, 5)),
        "fcf_cagr_5y": pct(cagr(fcf, 5)),
        "roic_avg_5y": None,
        "roe_avg_5y": None,
        "fcf_positive_5y": None,
        "fcf_positive_10y": None,
        "share_count_change_5y": pct(cagr(dilsh, 5)),
        "gross_margin_trend_5y": None,
        "operating_margin_trend_5y": None,
    }

    def avg(key, k=5):
        vals = [r[key] for r in rows[-k:] if r[key] is not None]
        return round(sum(vals) / len(vals), 1) if vals else None

    agg["roic_avg_5y"] = avg("roic")
    agg["roe_avg_5y"] = avg("roe")
    f5 = [r["fcf"] for r in rows[-5:] if r["fcf"] is not None]
    agg["fcf_positive_5y"] = (len(f5) == 5 and all(x > 0 for x in f5)) if f5 else None
    f10 = [r["fcf"] for r in rows if r["fcf"] is not None]
    agg["fcf_positive_10y"] = (len(f10) == n and all(x > 0 for x in f10)) if f10 else None
    for key, out in (("gross_margin", "gross_margin_trend_5y"),
                     ("operating_margin", "operating_margin_trend_5y")):
        a, b = rows[-5][key] if n >= 5 else None, rows[-1][key]
        agg[out] = None if (a is None or b is None) else round(b - a, 1)

    # PEG con el crecimiento de BPA a 5 anos, no con el del ultimo ejercicio
    pe, g = last("pe"), agg["eps_cagr_5y"]
    agg["pe_latest"] = pe
    agg["peg_5y"] = None if (pe is None or not g or g <= 0) else round(pe / g, 2)
    agg["fcf_yield_latest"] = last("fcf_yield")

    # Cifras del ultimo ejercicio, para que el dashboard recalcule P/E, PEG y
    # FCF yield con el precio en vivo en vez de con el cierre del ejercicio.
    agg["latest_fiscal_year"] = last("year")
    agg["diluted_shares_latest"] = last("diluted_shares")
    agg["net_income_latest"] = last("revenue") and None
    agg["net_income_latest"] = ni[-1] if ni else None
    agg["fcf_latest"] = last("fcf")
    agg["revenue_latest"] = last("revenue")
    agg["equity_latest"] = equity[-1] if equity else None

    missing = sorted({k for r in rows for k, v in r.items() if v is None})
    return {
        "ticker": d.get("ticker"),
        "company": d.get("company"),
        "fiscal_dates": dates,
        "units": "millones de USD; margenes, crecimientos y rentabilidades en %",
        "aggregates": agg,
        "by_year": rows,
        "campos_incompletos": missing,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    d = json.loads(Path(a.src).read_text(encoding="utf-8"))
    res = compute(d)
    txt = json.dumps(res, indent=2, ensure_ascii=False) + "\n"
    if a.out:
        Path(a.out).write_text(txt, encoding="utf-8")
        print(f"escrito {a.out}")
    else:
        print(txt)


if __name__ == "__main__":
    main()
