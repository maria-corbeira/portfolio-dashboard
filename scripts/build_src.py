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
EMPRESAS = {"MSFT": "Microsoft Corporation", "META": "Meta Platforms, Inc.",
            "UBER": "Uber Technologies, Inc.", "ISRG": "Intuitive Surgical, Inc.",
            "NVDA": "NVIDIA Corporation", "WMT": "Walmart Inc.",
            "IBM": "International Business Machines Corporation",
            "AMZN": "Amazon.com, Inc.", "AAPL": "Apple Inc.",
            "CVX": "Chevron Corporation"}


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

    # El impuesto lleva signo: negativo cuando es gasto, POSITIVO cuando es un
    # ingreso fiscal (Uber 2024: +5.758 por liberacion de provision). Por eso se
    # resta con su signo. Usar +|impuesto| inflaria el resultado antes de
    # impuestos justo en los anos en que la empresa se apunta un credito fiscal.
    ebt = [None if (ni is None or t is None) else ni - t
           for ni, t in zip(I["net_income"], I["income_tax"])]
    derivadas.append("EBT Incl. Unusual Items = Net Income - Income Tax Expense (con signo)")

    # Algunos emisores no etiquetan OperatingIncomeLoss en absoluto (Chevron, los diez
    # ejercicios). Sin resultado de explotacion no hay margen operativo, ni EBITDA, ni
    # cobertura de intereses, ni ROIC. Se deriva como EBIT = EBT + gasto financiero, que es
    # aritmetica sobre cifras publicadas. OJO CON LO QUE INCLUYE: al partir del resultado
    # antes de impuestos, arrastra tambien los ingresos no operativos (resultado de
    # participadas, plusvalias por venta de activos) y los deterioros. En una petrolera eso
    # no es residual. Solo se hace si la fila viene ENTERA a null: si el emisor la publica
    # aunque sea a medias, se respeta lo publicado.
    opinc = I["operating_income"]
    if all(v is None for v in opinc):
        opinc = [None if (e is None or ie is None) else e + ie
                 for e, ie in zip(ebt, I["interest_expense"])]
        if any(v is not None for v in opinc):
            derivadas.append("Operating Income = EBT + Interest Expense (el emisor no etiqueta "
                             "OperatingIncomeLoss; incluye resultados no operativos y "
                             "deterioros)")

    da = col(C, "depreciation_amortization")
    ebitda = [None if (o is None or d is None) else o + d
              for o, d in zip(opinc, da)]
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

    precios = [None] * n
    pf = RAW / "_precios.json"
    if pf.exists():
        px = json.loads(pf.read_text(encoding="utf-8"))["precios"].get(ticker)
        if px:
            assert len(px) == n, f"{ticker}: {len(px)} precios para {n} ejercicios"
            precios = px

    # Control: BPA x acciones diluidas ~= beneficio neto. Es lo que detecta que
    # el BPA y las acciones esten en bases de split distintas.
    split_ok, split_detalle = True, []
    for i in range(n):
        e, sh, b = I["eps_diluted"][i], I["diluted_shares"][i], I["net_income"][i]
        if None in (e, sh, b) or b <= 0 or e <= 0:
            continue
        desv = abs(e * sh / b - 1)
        if desv > 0.05:
            split_ok = False
            split_detalle.append(f"{dates[i][:4]}: BPA x acciones = {e*sh:,.0f} "
                                 f"frente a beneficio {b:,.0f} ({desv*100:.1f}%)")

    fcf = [None if (o is None or x is None) else o + x
           for o, x in zip(C["cfo"], C["capex"])]
    derivadas.append("Free Cash Flow = Cash from Operations + Capital Expenditure")
    neg = lambda s: [None if v is None else -abs(v) for v in s]

    return {
        "company": EMPRESAS[ticker], "ticker": ticker, "fiscal_dates": dates,
        "sheets": {
            "7.TIKR_IS": {
                "Total Revenues": I["revenue"], "Cost of Goods Sold": I["cogs"],
                "Gross Profit": gross, "Operating Income": opinc,
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
            # El P/E historico se calcula como precio/BPA, que no necesita el
            # recuento de acciones. La capitalizacion se deja vacia: sin ella el
            # FCF yield por ejercicio sale n.d., preferible a aproximarla.
            "10.TIKR_Val": {"Market Cap (MM)": [None] * n, "Price": precios},
        },
        "notas": {
            "fuente": "data.sec.gov/api/xbrl/companyconcept, hecho con 'filed' mas reciente por "
                      "ejercicio (cifras reexpresadas cuando las hay)",
            "extraido": "2026-09-05", "derivadas": derivadas, "deuda_incompleta": incompleta,
            "control_splits": {"cuadra": split_ok, "desviaciones": split_detalle},
            "market_cap_historico": "no disponible en esta sesion: sin fuente de precios historicos. "
                                    "P/E y FCF yield por ejercicio salen vacios; los actuales se "
                                    "calculan con el precio en vivo.",
            "discontinuidad": isj.get("discontinuidad"),
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
