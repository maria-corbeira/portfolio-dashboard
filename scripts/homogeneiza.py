#!/usr/bin/env python3
"""
Post-proceso de las extracciones crudas de la SEC, antes de build_src.py.

Hace dos cosas que un subagente extractor no puede hacer solo, porque exigen mirar la
serie entera y no un concepto XBRL aislado:

1. HOMOGENEIZAR SPLITS. La SEC publica el BPA y las acciones tal como se reportaron en
   cada momento. Cada 10-K solo reexpresa su ventana comparativa de tres ejercicios, asi
   que en una serie de diez conviven dos o tres bases distintas. Sin homogeneizar, el BPA
   por ano no es comparable y el P/E historico sale mal.

2. DERIVAR PARTIDAS QUE EL EMISOR NO ETIQUETA, solo con aritmetica sobre cifras
   publicadas y dejando constancia. Nunca una estimacion.

Es IDEMPOTENTE: cada fichero se marca con la clave "homogeneizado" y no se vuelve a tocar.

    python3 scripts/homogeneiza.py            # todos los tickers configurados
    python3 scripts/homogeneiza.py WMT        # solo uno
"""
import json
import sys
from datetime import date
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "fundamentals" / "raw"

# --- Splits -------------------------------------------------------------------------
# factor por ejercicio, en el orden de fiscal_dates. El BPA se DIVIDE y las acciones se
# MULTIPLICAN, para llevar los ejercicios antiguos a la base vigente hoy.
#
# WMT: split 3:1 del 26-feb-2024. Los datos XBRL con `filed` mas reciente traen FY2022-26
# ya reexpresados (entran en la ventana comparativa de los 10-K de FY2024 y FY2025), pero
# FY2017-21 conservan la base original. El salto se ve en las acciones diluidas:
# 2.847 M en FY2021 frente a 8.415 M en FY2022.
SPLITS = {
    "WMT": {
        "factores": [3, 3, 3, 3, 3, 1, 1, 1, 1, 1],
        "nota": "split 3:1 del 26-feb-2024; FY2017-FY2021 venian en la base anterior",
    },
}

# --- Minoritarios -------------------------------------------------------------------
# Walmart no etiqueta us-gaap:Liabilities (404 en los diez ejercicios), asi que el pasivo
# total se deriva como Activo - Patrimonio incluyendo minoritarios. Estos son la
# diferencia entre StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest
# y StockholdersEquity, leidos de la SEC en la misma extraccion del balance.
NCI = {
    "WMT": [2737, 2953, 7138, 6883, 6606, 8638, 7061, 6488, 6408, 6270],
}


# --- Ceros verificados --------------------------------------------------------------
# Un campo vacio NO es un cero, y por defecto se propaga el vacio. La excepcion es cuando
# se ha comprobado que la partida NO EXISTE en el balance del emisor. Aqui solo entran
# campos con esa comprobacion hecha y descrita.
#
# WMT / short_term_investments: los tres tags de la cascada dan 404 en los diez ejercicios.
# Comprobado por el metodo de la suma sobre datos de la SEC: el residuo
#   AssetsCurrent - (cash + ReceivablesNetCurrent + InventoryNet + PrepaidExpenseAndOtherAssetsCurrent)
# vale CERO EXACTO al millon en los diez ejercicios, asi que no queda hueco en el activo
# corriente donde puedan estar bajo otro tag. Walmart no tiene inversiones a corto plazo.
# Sin esto, la deuda neta y el ROIC de Walmart salen n.d. en los diez anos.
#
# IBM / short_term_investments (solo 2021-2025): OJO, la evidencia aqui es MAS DEBIL que en
# Walmart y conviene saberlo. Los cinco tags candidatos no tienen ni un solo hecho de 2021 en
# adelante (ausencia total, no filtrado por dimension), lo que encaja con que IBM simplificara
# la tesoreria tras el spin-off de Kyndryl. Pero el metodo de la suma NO pudo confirmarlo: la
# financiacion a clientes de IBM Global Financing va bajo un tag de extension propio, fuera de
# us-gaap, y domina el residuo del activo corriente con miles de millones.
# Se aplica el cero por MATERIALIDAD, no por prueba: las inversiones a corto de IBM valian
# 600-700 M$ cuando las reportaba, frente a un capital invertido de 67.000-85.000 M$. Aunque
# siguieran existiendo, el ROIC se moveria un 1% como mucho. La regla del vacio existe para
# evitar errores como el de Microsoft, donde tratar la caja como cero hundia el ROIC del 50%
# al 16,6%: un 200% de error. Aqui es un 1%, y la alternativa es quedarse sin ROIC en los
# cinco ultimos ejercicios. Queda dicho tambien en la ficha de IBM del dashboard.
CEROS_VERIFICADOS = {
    "IBM": {"short_term_investments": {
            "desde": "2021",
            "motivo":
            "los cinco tags candidatos no tienen ningun hecho desde 2021, coherente con la "
            "simplificacion de tesoreria tras el spin-off de Kyndryl. NO se pudo confirmar por "
            "el metodo de la suma (la financiacion a clientes usa un tag propio de IBM y tapa "
            "el residuo), asi que se aplica por materialidad: 600-700 M$ frente a un capital "
            "invertido de 67.000-85.000 M$ mueven el ROIC un 1% como mucho"}},
    "WMT": {"short_term_investments":
            "los tres tags dan 404 y el residuo del activo corriente es cero exacto en los "
            "diez ejercicios (cash + clientes + existencias + anticipos = AssetsCurrent), "
            "asi que la partida no existe; no es un dato ausente"},
}


# --- Signos -------------------------------------------------------------------------
# Convencion del proyecto: el impuesto va NEGATIVO cuando es gasto y POSITIVO cuando es un
# ingreso fiscal (Uber 2024: +5.758 por liberacion de provision). build_src.py calcula
# EBT = beneficio neto - impuesto CON SIGNO, y metrics.py saca de ahi el tipo efectivo y,
# con el, el NOPAT y el ROIC. Si un extractor devuelve el impuesto en positivo, el EBT sale
# restado en vez de sumado (WMT FY2025: 13.284 en vez de 25.588), el tipo efectivo se sale
# del rango [0, 0.6], se anula, y el ROIC desaparece de los diez ejercicios sin ruido.
# Por eso se normaliza aqui, de forma explicita por ticker y con comprobacion.
SIGNOS = {
    "WMT": ["income_tax"],
}


# --- Discontinuidades de perimetro ---------------------------------------------------
# Una escision parte la serie en dos empresas distintas. Los ejercicios anteriores al ano
# de corte NO son comparables con los posteriores, asi que cualquier CAGR que cruce esa
# frontera mide el trozo que se marcho, no el crecimiento del negocio.
DISCONTINUIDADES = {
    "IBM": {"desde": "2019",
            "motivo": "spin-off de Kyndryl (noviembre de 2021). IBM reexpreso 2019 y 2020 "
                      "para presentar Kyndryl como actividad discontinuada, pero nunca "
                      "reexpreso 2016-2018, que siguen incluyendola. Por eso las ventas caen "
                      "de 79.591 M$ en 2018 a 57.714 M$ en 2019: no es un desplome, son dos "
                      "perimetros distintos. El CAGR de ventas a 10 anios daba -1,9% anual "
                      "por esto; el de 5 anios (2020-2025) si es homogeneo."},
}


def marca_discontinuidad(ticker: str) -> list:
    disc = DISCONTINUIDADES.get(ticker)
    if not disc:
        return []
    p = RAW / f"{ticker}_is.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    if d.get("discontinuidad"):
        return [f"{ticker}: discontinuidad ya marcada, no se toca"]
    d["discontinuidad"] = disc
    d.setdefault("avisos", []).append(
        f"DISCONTINUIDAD DE PERIMETRO desde {disc['desde']}: {disc['motivo']}")
    p.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return [f"{ticker}: discontinuidad marcada desde {disc['desde']}"]


def normaliza_signos(ticker: str) -> list:
    campos = SIGNOS.get(ticker)
    if not campos:
        return []
    p = RAW / f"{ticker}_is.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    if "signos" in d.get("homogeneizado", {}):
        return [f"{ticker}: signos ya normalizados, no se tocan"]

    out = []
    for campo in campos:
        serie = d["rows"][campo]
        vals = [v for v in serie if v is not None]
        # Solo se invierte si TODOS son positivos: una serie mixta ya lleva la convencion
        # buena y darle la vuelta destrozaria los anos de credito fiscal.
        assert vals and all(v > 0 for v in vals), \
            f"{ticker}/{campo}: la serie no es toda positiva, revisala a mano: {serie}"
        d["rows"][campo] = [None if v is None else -v for v in serie]
        d.setdefault("avisos", []).append(
            f"{campo}: signo invertido el {date.today().isoformat()}. El extractor lo devolvio "
            f"en positivo y la convencion del proyecto es negativo cuando es gasto, porque "
            f"build_src.py calcula EBT = beneficio neto - impuesto con signo.")
        out.append(f"{ticker}: {campo} invertido -> {d['rows'][campo][-3:]}")

    d.setdefault("homogeneizado", {})["signos"] = campos
    p.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def aplica_ceros(ticker: str) -> list:
    campos = CEROS_VERIFICADOS.get(ticker)
    if not campos:
        return []
    p = RAW / f"{ticker}_bs.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    if "ceros" in d.get("homogeneizado", {}):
        return [f"{ticker}: ceros ya aplicados, no se tocan"]

    n, out = len(d["fiscal_dates"]), []
    for campo, cfg in campos.items():
        # cfg puede ser el motivo suelto (aplica a los diez ejercicios) o un dict con
        # "desde", para los casos en que la partida existio y dejo de existir.
        motivo = cfg if isinstance(cfg, str) else cfg["motivo"]
        desde = None if isinstance(cfg, str) else cfg.get("desde")
        serie = list(d["rows"].get(campo, [None] * n))

        afectados = [i for i, f in enumerate(d["fiscal_dates"])
                     if desde is None or f[:4] >= str(desde)]
        # Nunca se pisa un dato que si publico la SEC.
        for i in afectados:
            assert serie[i] is None, \
                f"{ticker}/{campo}: {d['fiscal_dates'][i][:4]} tiene valor de la SEC ({serie[i]}), no se pisa"
        if desde is not None:
            intactos = [i for i in range(n) if i not in afectados]
            assert any(serie[i] is not None for i in intactos), \
                f"{ticker}/{campo}: no hay ningun valor real antes de {desde}, revisa la config"

        for i in afectados:
            serie[i] = 0
        d["rows"][campo] = serie
        rango = f"desde {desde}" if desde else f"los {n} ejercicios"
        d.setdefault("avisos", []).append(
            f"{campo} fijado a 0 {rango} el {date.today().isoformat()}, NO por defecto: {motivo}.")
        out.append(f"{ticker}: {campo} = 0 en {len(afectados)} ejercicios ({rango})")

    d.setdefault("homogeneizado", {})["ceros"] = sorted(campos)
    p.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def aplica_split(ticker: str) -> list:
    cfg = SPLITS.get(ticker)
    if not cfg:
        return []
    p = RAW / f"{ticker}_is.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    if "split" in d.get("homogeneizado", {}):
        return [f"{ticker}: split ya aplicado, no se toca"]

    factores = cfg["factores"]
    r = d["rows"]
    assert len(factores) == len(d["fiscal_dates"]), f"{ticker}: factores descuadrados"

    antes = list(zip(r["eps_diluted"], r["diluted_shares"]))
    r["eps_diluted"] = [None if v is None else round(v / f, 6)
                        for v, f in zip(r["eps_diluted"], factores)]
    r["diluted_shares"] = [None if v is None else round(v * f)
                           for v, f in zip(r["diluted_shares"], factores)]

    # Control: BPA x acciones ~= beneficio neto. Es invariante al split (uno se divide y
    # el otro se multiplica), asi que si se rompe aqui es que algo mas iba mal.
    fallos = []
    for i, (e, s, n) in enumerate(zip(r["eps_diluted"], r["diluted_shares"], r["net_income"])):
        if None in (e, s, n) or n <= 0:
            continue
        desv = abs(e * s / n - 1)
        if desv > 0.05:
            fallos.append(f"{d['fiscal_dates'][i][:4]}: {desv*100:.1f}%")
    assert not fallos, f"{ticker}: BPA x acciones se desvia del beneficio en {fallos}"

    d.setdefault("homogeneizado", {})["split"] = cfg["nota"]
    d.setdefault("avisos", []).append(
        f"BPA y acciones diluidas homogeneizados el {date.today().isoformat()}: {cfg['nota']}. "
        f"Factores por ejercicio: {factores}. El BPA se dividio y las acciones se multiplicaron. "
        f"Control BPA x acciones ~= beneficio neto: OK en los {len(factores)} ejercicios.")
    p.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    cambios = [f"{d['fiscal_dates'][i][:4]}: BPA {a[0]}->{r['eps_diluted'][i]}, "
               f"acciones {a[1]}->{r['diluted_shares'][i]}"
               for i, a in enumerate(antes) if factores[i] != 1]
    return [f"{ticker}: split aplicado a {len(cambios)} ejercicios"] + cambios[:3]


def deriva_pasivo(ticker: str) -> list:
    nci = NCI.get(ticker)
    if not nci:
        return []
    p = RAW / f"{ticker}_bs.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    if "pasivo_derivado" in d.get("homogeneizado", {}):
        return [f"{ticker}: pasivo ya derivado, no se toca"]

    r = d["rows"]
    if any(v is not None for v in r.get("total_liabilities", [])):
        return [f"{ticker}: total_liabilities ya viene de la SEC, no se deriva"]

    assert len(nci) == len(d["fiscal_dates"]), f"{ticker}: NCI descuadrado"
    r["total_liabilities"] = [
        None if (a is None or e is None or m is None) else a - (e + m)
        for a, e, m in zip(r["total_assets"], r["total_equity"], nci)]

    # Control: el pasivo derivado tiene que ser positivo y mayor que el corriente.
    for i, (tl, tc) in enumerate(zip(r["total_liabilities"], r["total_current_liabilities"])):
        if tl is None or tc is None:
            continue
        assert tl > 0, f"{ticker} {d['fiscal_dates'][i][:4]}: pasivo derivado {tl} <= 0"
        assert tl >= tc, (f"{ticker} {d['fiscal_dates'][i][:4]}: pasivo total {tl} "
                          f"menor que el corriente {tc}")

    d.setdefault("homogeneizado", {})["pasivo_derivado"] = True
    d.setdefault("avisos", []).append(
        f"total_liabilities DERIVADO el {date.today().isoformat()} como Activo total - "
        f"(Patrimonio atribuible + Minoritarios), porque el emisor no etiqueta us-gaap:Liabilities "
        f"(404 en los diez ejercicios). Es aritmetica sobre cifras publicadas, no una estimacion. "
        f"Minoritarios usados: {nci}.")
    p.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return [f"{ticker}: total_liabilities derivado -> {r['total_liabilities'][-3:]}"]


def main() -> int:
    tickers = sys.argv[1:] or sorted(set(SPLITS) | set(NCI) | set(CEROS_VERIFICADOS)
                                     | set(SIGNOS) | set(DISCONTINUIDADES))
    for t in tickers:
        for linea in (marca_discontinuidad(t) + normaliza_signos(t) + aplica_split(t)
                      + deriva_pasivo(t) + aplica_ceros(t)):
            print(" ", linea)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
