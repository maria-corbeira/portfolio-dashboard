#!/usr/bin/env python3
"""
Convierte las extracciones crudas de la SEC (fundamentals/raw/<TICKER>_{is,bs,cf}.json)
al formato de plantilla IDC que consume scripts/metrics.py.

Todas las derivaciones son aritmetica sobre cifras publicadas, nunca estimaciones:
  gross_profit = ventas - coste de ventas    (solo si la empresa no etiqueta GrossProfit)
  ebt          = beneficio neto + |impuesto| (identidad validada contra la SEC en GOOGL)
  ebitda       = resultado de explotacion + D&A   (vacio si D&A no es fiable)
  total_debt   = deuda corto + porcion corriente + deuda largo + arrendamientos
  net_debt     = total_debt - (caja + inversiones a corto)
  fcf          = flujo de explotacion + capex     (el capex ya viene negativo)

Un componente ausente NUNCA se sustituye por cero: o se propaga el vacio, o se suma
solo lo disponible dejando constancia en notas.deuda_incompleta.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "fundamentals" / "raw"
OUT = ROOT / "fundamentals"

DEBT_PARTS = [
    ("short_term_borrowings", "deuda a corto"),
    ("current_portion_ltd", "porcion corriente"),
    ("long_term_debt", "deuda a largo"),
    ("finance_lease_current", "arrend. financiero corriente"),
    ("finance_lease_noncurrent", "arrend. financiero no corriente"),
    ("operating_lease_current", "arrend. operativo corriente"),
    ("operating_lease_noncurrent", "arrend. operativo no corriente"),
]
EMPRESAS = {"MSFT": "Microsoft Corporation", "META": "Meta Platforms, Inc."}


def build(ticker: str) -> dict:
    isj = json.loads((RAW / f"{ticker}_is.json").read_text(encoding="utf-8"))
    bsj = json.loads((RAW / f"{ticker}_bs.json").read_text(encoding="utf-8"))
    cfj = json.loads((RAW / f"{ticker}_cf.json").read_text(encoding="utf-8"))
    dates = isj["fiscal_dates"]
    assert bsj["fiscal_dates"] == dates and cfj["fiscal_dates"] == dates, "fechas descuadradas"
    n = len(dates)
    I, B, C = isj["rows"], bsj["rows"], cfj["rows"]
    col = lambda d, k: d.get(k) or [None] * n
    for src in (I, B, C):
        for k, v in src.items():
            assert len(v) == n, f"{ticker}/{k}: {len(v)} valores, se esperaban {n}"

    derivadas = []
    gross = col(I, "gross_profit")
    if all(v is None for v in gross):
        gross = [None if (r is None or c is None) else r - c
                 for r, c in zip(I["revenue"], I["cogs"])]
        derivadas.append("Gross Profit = Total Revenues - Cost of Goods Sold "
                         "(la empresa no etiqueta GrossProfit en XBRL)")

    ebt = [None if (ni is None or t is None) else ni + abs(t)
           for ni, t in zip(I["net_income"], I["income_tax"])]
    derivadas.append("EBT Incl. Unusual Items = Net Income + |Income Tax Expense|")

    da = col(C, "depreciation_amortization")
    ebitda = [None if (o is None or d is None) else o + d
              for o, d in zip(I["operating_income"], da)]
    derivadas.append("EBITDA vacio: sin dato fiable de amortizacion"
                     if all(v is None for v in ebitda)
                     else "EBITDA = Operating Income + Depreciation & Amortization")

    total_debt, net_debt, cash_sti, incompleta = [], [], [], []
    for i in range(n):
        piezas = {etiq: col(B, k)[i] for k, etiq in DEBT_PARTS}
        presentes = {k: v for k, v in piezas.items() if v is not None}
        ausentes = [k for k, v in piezas.items() if v is None]
        td = sum(presentes.values()) if presentes else None
        total_debt.append(td)
        if presentes and ausentes:
            incompleta.append(f"{dates[i][:4]}: suma sin {', '.join(ausentes)}")
        c, sti = col(B, "cash")[i], col(B, "short_term_investments")[i]
        cs = c + sti if (c is not None and sti is not None) else None
        cash_sti.append(cs)
        net_debt.append(None if (td is None or cs is None) else td - cs)
    derivadas += ["Total Debt = suma de las piezas de deuda y arrendamiento disponibles",
                  "Net Debt = Total Debt - (Cash And Equivalents + Short Term Investments)"]

    fcf = [None if (o is None or x is None) else o + x
           for o, x in zip(C["cfo"], C["capex"])]
    derivadas.append("Free Cash Flow = Cash from Operations + Capital Expenditure")
    neg = lambda s: [None if v is None else -abs(v) for v in s]

    return {
        "company": EMPRESAS[ticker], "ticker": ticker, "fiscal_dates": dates,
        "sheets": {
            "7.TIKR_IS": {
                "Total Revenues": I["revenue"], "Cost of Goods Sold": I["cogs"],
                "Gross Profit": gross, "Operating Income": I["operating_income"],
                "EBITDA": ebitda, "Interest Expense": I["interest_expense"],
                "EBT Incl. Unusual Items": ebt, "Income Tax Expense": I["income_tax"],
                "Net Income": I["net_income"], "Diluted EPS Excl Extra Items": I["eps_diluted"],
                "Weighted Average Diluted Shares Outstanding": I["diluted_shares"],
                "R&D Expenses": col(I, "rd_expense")},
            "8.TIKR_BS": {
                "Cash And Equivalents": B["cash"],
                "Total Cash And Short Term Investments": cash_sti,
                "Total Current Assets": B["total_current_assets"],
                "Total Current Liabilities": B["total_current_liabilities"],
                "Total Assets": B["total_assets"], "Total Liabilities": col(B, "total_liabilities"),
                "Total Equity": B["total_equity"], "Total Debt": total_debt, "Net Debt": net_debt},
            "9.TIKR_CF": {
                "Cash from Operations": C["cfo"], "Capital Expenditure": C["capex"],
                "Free Cash Flow": fcf, "Depreciation & Amortization": da,
                "Stock-Based Compensation": C["stock_based_compensation"],
                "Repurchase of Common Stock": neg(col(C, "buybacks")),
                "Common & Preferred Stock Dividends Paid": neg(col(C, "dividends_paid"))},
            "10.TIKR_Val": {"Market Cap (MM)": [None] * n, "Price": [None] * n},
        },
        "notas": {
            "fuente": "data.sec.gov/api/xbrl/companyconcept, hecho con 'filed' mas reciente por "
                      "ejercicio (cifras reexpresadas cuando las hay)",
            "extraido": "2026-09-05", "derivadas": derivadas, "deuda_incompleta": incompleta,
            "market_cap_historico": "no disponible en esta sesion: sin fuente de precios historicos. "
                                    "P/E y FCF yield por ejercicio salen vacios; los actuales se "
                                    "calculan con el precio en vivo.",
            "tags_is": isj.get("tags_usados"), "tags_bs": bsj.get("tags_usados"),
            "tags_cf": cfj.get("tags_usados"),
            "avisos_extraccion": isj.get("avisos", []) + bsj.get("avisos", []) + cfj.get("avisos", []),
        },
    }


def main() -> None:
    for t in EMPRESAS:
        p = OUT / f"{t}.src.json"
        p.write_text(json.dumps(build(t), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"escrito {p.name}")


if __name__ == "__main__":
    main()
