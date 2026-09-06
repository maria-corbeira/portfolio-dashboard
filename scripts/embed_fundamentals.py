#!/usr/bin/env python3
"""
Incrusta fundamentals/*.json dentro de index.html, entre los marcadores
// <<<FUNDAMENTALS y // FUNDAMENTALS>>>.

Se incrusta en vez de cargarse con fetch() para que el dashboard funcione
tambien abierto como fichero local (file:// bloquea fetch por CORS).

Uso: python3 scripts/embed_fundamentals.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
SRC = ROOT / "fundamentals"
START, END = "// <<<FUNDAMENTALS", "// FUNDAMENTALS>>>"

# Se incrusta solo lo que el dashboard usa: agregados + serie anual recortada.
KEEP_YEAR = ["year", "revenue", "revenue_growth", "gross_margin", "operating_margin",
             "net_margin", "roe", "roic", "interest_coverage", "debt_to_equity",
             "net_debt_ebitda", "current_ratio", "eps_diluted", "eps_growth", "net_income", "net_income_growth",
             "cfo", "capex", "fcf", "fcf_margin", "fcf_growth", "sbc_pct_revenue",
             "diluted_shares", "market_cap", "price_close", "pe", "fcf_yield"]


def main() -> int:
    data = {}
    for f in sorted(SRC.glob("*.json")):
        if f.name.startswith("_") or f.name.endswith(".src.json"):
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        data[d["ticker"]] = {
            "company": d.get("company"),
            "units": d.get("units"),
            "aggregates": d["aggregates"],
            "by_year": [{k: r.get(k) for k in KEEP_YEAR} for r in d["by_year"]],
        }

    html = INDEX.read_text(encoding="utf-8")
    if START not in html or END not in html:
        print("ERROR: faltan los marcadores en index.html")
        return 1
    a = html.index(START) + len(START)
    b = html.index(END)
    block = ("\n// Generado por scripts/embed_fundamentals.py — no editar a mano.\n"
             "const fundamentals = "
             + json.dumps(data, ensure_ascii=False, separators=(",", ":"))
             + ";\n")
    INDEX.write_text(html[:a] + block + html[b:], encoding="utf-8")
    print(f"incrustados {len(data)} tickers: {', '.join(data)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
