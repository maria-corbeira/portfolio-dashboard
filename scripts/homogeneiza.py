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
#
# AMZN: split 20:1 del 6-jun-2022. El salto se ve en las acciones diluidas y en el BPA; los
# factores se fijan tras leer la serie que devolvio la SEC, no a priori.
#
# AAPL: split 4:1 del 28-ago-2020, pero el salto NO esta en FY2020. Esta entre FY2017 y
# FY2018, porque la regla del `filed` mas reciente recoge FY2018 y FY2019 ya reexpresados en
# los 10-K de 2020 y 2021, mientras que FY2016 y FY2017 se quedaron fuera de toda ventana
# comparativa posterior y conservan la base antigua. Se ve en las acciones: 5.252 M en FY2017
# frente a 20.000 M en FY2018.
SPLITS = {
    "AAPL": {
        "factores": [4, 4, 1, 1, 1, 1, 1, 1, 1, 1],
        "nota": "split 4:1 del 28-ago-2020; FY2016-FY2017 venian en la base anterior",
    },
    "AMZN": {
        "factores": [20, 20, 20, 20, 1, 1, 1, 1, 1, 1],
        "nota": "split 20:1 del 6-jun-2022; FY2016-FY2019 venian en la base anterior",
    },
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
#
# AMZN: tampoco etiqueta us-gaap:Liabilities (404 en los diez ejercicios), y ademas el tag
# StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest tambien da 404. No es
# un hueco: el balance de Amazon no tiene linea de minoritarios, su patrimonio es directamente
# "Total stockholders equity". Por eso los minoritarios van a cero explicito y el pasivo sale
# como Activo - Patrimonio a secas. El control de deriva_pasivo (pasivo total >= pasivo
# corriente y > 0) lo comprueba en los diez ejercicios.
NCI = {
    "WMT": [2737, 2953, 7138, 6883, 6606, 8638, 7061, 6488, 6408, 6270],
    "AMZN": [0] * 10,
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


# --- Valores publicados bajo un tag que la SEC renombro ------------------------------
# No es una derivacion ni una estimacion: es el MISMO hecho de la SEC, publicado bajo el
# nombre que tenia antes de un cambio de norma. Se rellena solo donde el extractor dejo
# hueco, nunca se pisa un valor existente.
#
# AMZN: la ASC 842 (adoptada en el ejercicio cerrado el 31-12-2019) renombro los
# "capital leases" como "finance leases". Los tags FinanceLeaseLiabilityCurrent y
# FinanceLeaseLiabilityNoncurrent no existen antes de 2019, pero los arrendamientos SI
# estaban en balance bajo CapitalLeaseObligationsCurrent / ...Noncurrent. Dejarlos vacios
# infravaloraba la deuda de Amazon en 17.370 M$ en 2018, frente a 23.495 M$ de deuda a
# largo: no era un vacio real. Lo que si es un vacio real en 2016-2018 son los
# arrendamientos OPERATIVOS, que antes de la ASC 842 no se reconocian en balance.
TAGS_ANTIGUOS = {
    # AAPL: hasta FY2017 las inversiones a corto se etiquetaban como
    # AvailableForSaleSecuritiesCurrent; despues Apple paso a MarketableSecuritiesCurrent, al
    # adoptar la ASU 2016-01. Es la misma linea del balance, "Short-term marketable
    # securities". Sin ella, la caja de FY2016 y FY2017 se quedaba en 20.000 M$ en vez de
    # 67.000 y 74.000, y la deuda neta y el ROIC de esos dos ejercicios salian mal.
    "AAPL": [{
        "estado": "bs",
        "valores": {"short_term_investments": {"2016": 46671, "2017": 53892}},
        "motivo":
            "inversiones a corto de FY2016 y FY2017 leidas de "
            "us-gaap:AvailableForSaleSecuritiesCurrent, el tag que Apple usaba antes de la ASU "
            "2016-01. Mismo importe en el 10-K y en los tres 10-Q siguientes de cada anio, sin "
            "reexpresiones. Los cuatro campos de arrendamientos siguen vacios en FY2016-FY2019 "
            "y eso SI es real: Apple adopto la ASC 842 en el primer trimestre de FY2020, asi "
            "que antes no habia nada que reconocer en balance.",
    }],
    # COP: ConocoPhillips NO desglosa la deuda a corto en papel comercial y porcion corriente
    # de la deuda a largo: presenta una sola linea, "Debt maturing within one year", bajo el
    # tag agregado DebtCurrent. Los dos tags que busca el extractor dan 404, y el extractor
    # hizo lo correcto al dejarlos vacios en vez de adivinar en cual de los dos cubos meter la
    # cifra. Se coloca aqui, en short_term_borrowings, que es el cubo que representa la deuda
    # a corto en `build_src.py`. Los diez valores estan verificados contra la fila del balance
    # en las paginas R de los 10-K en ocho de los diez ejercicios.
    "COP": [{
        "estado": "bs",
        "valores": {
            "short_term_borrowings": {
                "2016": 1089, "2017": 2575, "2018": 112, "2019": 105, "2020": 619,
                "2021": 1200, "2022": 417, "2023": 1074, "2024": 1035, "2025": 1020},
            # Las inversiones a corto de 2021 y 2022 tampoco llegaron por la via XBRL, y sin
            # ellas el ROIC de esos dos ejercicios salia n.d. porque el capital invertido resta
            # caja mas inversiones. Leidas del mismo balance del 10-K de FY2022: en esa misma
            # tabla la caja, el activo corriente y el activo total de los dos anios coinciden
            # EXACTOS con lo ya extraido, asi que la fuente esta contrastada.
            "short_term_investments": {"2021": 446, "2022": 2785},
        },
        "motivo":
            "deuda a corto leida de us-gaap:DebtCurrent, la unica linea que publica COP para "
            "los vencimientos a un anio: ShortTermBorrowings y LongTermDebtCurrent dan 404 "
            "porque no desglosa. Se pone entera en short_term_borrowings y current_portion_ltd "
            "se queda vacio, para no contarla dos veces. Verificado contra la fila 'Debt "
            "maturing within one year' de las paginas R de los 10-K en 2016, 2017 y 2020-2025. "
            "Las inversiones a corto de 2021 (446) y 2022 (2.785) salen de la pagina R5 del 10-K de "
            "FY2022 (expediente 0001163165-23-000006), cuya caja, activo corriente y activo total "
            "de los dos anios coinciden exactos con los ya extraidos.",
    }],
    # CVX: aqui el hueco NO lo causo un tag renombrado, sino una limitacion de la herramienta.
    # Los ficheros companyconcept de LongTermDebtNoncurrent y CashAndCashEquivalentsAt
    # CarryingValue de Chevron son enormes y WebFetch los trunca POR EL FINAL; como los hechos
    # van en orden cronologico ascendente, lo que se pierde es justo lo reciente. Se recuperaron
    # de las paginas R del informe financiero de cada 10-K, que son tablas HTML pequeñas con el
    # balance consolidado de dos ejercicios. Es el mismo hecho publicado por Chevron, leido en
    # otro sitio. Cada valor se confirmo en DOS 10-K distintos (el del ejercicio y el siguiente,
    # que lo repite como comparativo) y el activo total de cada tabla se contrasto con las
    # cifras ya verificadas: 2019=237.428, 2024=256.938, 2025=324.012 M$.
    "CVX": [{
        "estado": "bs",
        "valores": {
            "long_term_debt": {"2018": 28733, "2019": 23691, "2020": 42767, "2021": 31113,
                               "2022": 21375, "2023": 20307, "2024": 20135, "2025": 39781},
            "cash": {"2019": 5686, "2024": 6781, "2025": 6293},
        },
        "motivo":
            "deuda a largo (2018-2025) y caja (2019, 2024, 2025) leidas de las paginas R del "
            "informe financiero de los 10-K de FY2019, FY2020, FY2021, FY2022, FY2023 y FY2025, "
            "porque el companyconcept de esos dos tags es demasiado grande y WebFetch lo trunca "
            "por el final. Cada importe aparece identico en dos 10-K distintos y el activo total "
            "de cada tabla cuadra con el ya verificado. No es una estimacion: es el dato "
            "publicado, leido por otra via.",
    }],
    "AMZN": [{
        "estado": "bs",
        "valores": {
            "finance_lease_current": {"2016": 4000, "2017": 5800, "2018": 7720},
            "finance_lease_noncurrent": {"2016": 5080, "2017": 8438, "2018": 9650},
        },
        "motivo":
            "arrendamientos financieros de 2016-2018 leidos de us-gaap:CapitalLeaseObligations"
            "Current y ...Noncurrent, el nombre que tenian antes de la ASC 842. Se tomo en cada "
            "fecha el hecho de 10-K con `filed` mas reciente, segun la regla del proyecto. Ojo: "
            "en ese 10-K posterior los importes corrientes de 2016 y 2017 vienen redondeados a "
            "centenas de millon (4.000 frente a 3.997 del 10-K original, 5.800 frente a 5.839); "
            "la diferencia es de 3 y 39 M$ sobre un balance de 83.000 y 131.310 M$.",
    }, {
        # AMZN 2024: los tres tags de la cascada de interest_expense (InterestExpense,
        # InterestExpenseDebt, InterestIncomeExpenseNet) dejan de tener hechos, pero el gasto
        # financiero SI esta publicado, bajo InterestExpenseNonoperating. FY2025 no aparece en
        # ningun tag de intereses: ese si queda vacio de verdad, y con el la cobertura de
        # intereses del ultimo ejercicio sale n.d.
        "estado": "is",
        "valores": {"interest_expense": {"2024": 2406}},
        "motivo":
            "gasto financiero de 2024 leido de us-gaap:InterestExpenseNonoperating (10-K filed "
            "2025-02-07), porque los tres tags de la cascada dejaron de usarse ese ano. FY2025 "
            "no existe en ningun tag de intereses y se queda vacio: no se estima.",
    }],
}


# --- Filas sustituidas por una serie alternativa completa --------------------------------
# Ultimo recurso, y solo cuando el problema NO es que falte el dato sino que la fila que trae
# el extractor no significa lo que el resto del pipeline cree. Sustituir una fila entera exige
# escribir aqui los diez valores y el motivo, y el codigo comprueba antes de escribir que la
# fila actual es la que se espera: no puede pisar otra cosa por descuido.
#
# CVX / revenue: Chevron presenta DOS cifras arriba de su cuenta de resultados, "Sales and
# other operating revenues" y "Total revenues and other income", que ademas suma el resultado
# de sus participadas (TCO, Angola LNG y demas) y las plusvalias por venta de activos. El tag
# de ventas solo existe desde 2018, porque nace con la ASC 606, y los dos tags antiguos
# (SalesRevenueNet y SalesRevenueGoodsNet) dan 404: Chevron nunca los uso. Asi que la unica
# serie COMPLETA de diez ejercicios es la del total. Se usa esa, en los diez anios, para no
# mezclar dos definiciones dentro de la misma serie. En FY2024 son 202.792 M$ en vez de
# 193.414: un 4,9% mas. Queda dicho en la ficha del dashboard.
#
# CVX / cogs: el extractor SI encontro CostOfGoodsAndServicesSold, pero en Chevron esa etiqueta
# recoge solo "Purchased crude oil and products", no un coste de ventas agregado: fuera quedan
# los gastos de explotacion, el agotamiento de reservas y los impuestos distintos del de
# sociedades. Dejarla puesta hacia que build_src.py derivase un "margen bruto" del 38-45% que
# no significa nada. Se anula: el margen bruto de Chevron sale n.d., que es la verdad.
SERIES_REEMPLAZADAS = {
    # COP / eps_diluted: el extractor trajo 6,40 para 2018, que es el valor de 2019 duplicado.
    # Lo detecto el control BPA x acciones ~= beneficio neto, que fallaba un 20% solo en ese
    # anio, y el extractor hizo lo correcto: lo reporto y NO lo toco. Pedir otra vez el mismo
    # concepto a la API devolvio una respuesta todavia peor (2019 = 6,07, que contradice
    # 7.189 / 1.123,54 = 6,40), asi que se fue a la pagina R2 del 10-K de FY2019
    # (0001193125-20-039954), que da 2019 = 6,40, 2018 = 5,32 y 2017 = -0,70, con un beneficio
    # neto de los tres anios identico al ya extraido. Solo cambia 2018.
    "COP": [{
        # Mismo caso exacto que Chevron: el tag existe, pero en una petrolera recoge solo la
        # compra de crudo y productos, no un coste de ventas agregado. Restarlo de los ingresos
        # daba un "margen bruto" del 56-68% que no significa nada para una empresa de
        # exploracion y produccion, porque deja fuera los costes de extraccion, el agotamiento
        # de reservas y los impuestos distintos del de sociedades.
        "estado": "is",
        "campo": "cogs",
        "espera_actual": [9994, 12475, 14294, 11842, 8078, 18158, 33971, 21975, 20012, 22325],
        "nueva": [None] * 10,
        "motivo":
            "us-gaap:CostOfGoodsAndServicesSold en COP es una partida parcial, no un coste de "
            "ventas agregado, igual que en Chevron. Se anula para que el margen bruto salga "
            "n.d. en vez de un 56-68% que no describe nada.",
    }, {
        "estado": "is",
        "campo": "eps_diluted",
        "espera_actual": [-2.91, -0.7, 6.4, 6.4, -2.51, 6.07, 14.57, 9.06, 7.81, 6.35],
        "nueva": [-2.91, -0.7, 5.32, 6.4, -2.51, 6.07, 14.57, 9.06, 7.81, 6.35],
        "motivo":
            "BPA diluido de 2018 corregido de 6,40 a 5,32. El 6,40 era el valor de 2019 "
            "duplicado: 6,40 x 1.175,54 M acciones daba 7.523 M$ frente a un beneficio neto "
            "real de 6.257 M$, un 20% de desviacion. El valor bueno se leyo de la pagina R2 "
            "del 10-K de FY2019 (expediente 0001193125-20-039954), que ademas repite el "
            "beneficio neto de 2017, 2018 y 2019 identico al ya extraido. Los otros nueve "
            "ejercicios no se tocan.",
    }],
    "CVX": [{
        "estado": "is",
        "campo": "revenue",
        "espera_actual": [None, None, 158902, 139865, 94471, 155606, 235717, 196913, 193414,
                          184432],
        "nueva": [114472, 141722, 166339, 146516, 94692, 162465, 246252, 200949, 202792,
                  189031],
        "motivo":
            "serie de us-gaap:Revenues, o sea 'Total revenues and other income'. Se usa esta y "
            "no la de ventas porque la de ventas solo existe desde 2018 (nace con la ASC 606) "
            "y los tags antiguos SalesRevenueNet y SalesRevenueGoodsNet dan 404. Incluye el "
            "resultado de participadas y las plusvalias por venta de activos, asi que en "
            "FY2024 son 202.792 M$ frente a 193.414 de ventas puras, un 4,9% mas.",
    }, {
        "estado": "is",
        "campo": "cogs",
        "espera_actual": [59321, 75765, 94578, 80113, 50488, 89372, 145416, 119196, 119206,
                          108214],
        "nueva": [None] * 10,
        "motivo":
            "us-gaap:CostOfGoodsAndServicesSold en Chevron es solo 'Purchased crude oil and "
            "products', no un coste de ventas agregado: no incluye gastos de explotacion, "
            "agotamiento de reservas ni impuestos distintos del de sociedades. Restarlo de los "
            "ingresos daba un falso margen bruto del 38-45%. Se anula para que el margen bruto "
            "salga n.d., que es lo que realmente se sabe.",
    }],
}


def reemplaza_series(ticker: str) -> list:
    out = []
    for cfg in SERIES_REEMPLAZADAS.get(ticker, []):
        p = RAW / f"{ticker}_{cfg['estado']}.json"
        d = json.loads(p.read_text(encoding="utf-8"))
        hechas = d.get("homogeneizado", {}).get("series_reemplazadas", [])
        if cfg["campo"] in hechas:
            out.append(f"{ticker}: {cfg['campo']} ya reemplazado, no se toca")
            continue
        actual = d["rows"][cfg["campo"]]
        assert actual == cfg["espera_actual"], (
            f"{ticker}/{cfg['campo']}: la fila actual no es la esperada, no se reemplaza.\n"
            f"  esperaba: {cfg['espera_actual']}\n  hay:      {actual}")
        assert len(cfg["nueva"]) == len(d["fiscal_dates"]), f"{ticker}: serie descuadrada"
        d["rows"][cfg["campo"]] = list(cfg["nueva"])
        d.setdefault("homogeneizado", {}).setdefault("series_reemplazadas", []).append(
            cfg["campo"])
        d.setdefault("avisos", []).append(
            f"Fila `{cfg['campo']}` REEMPLAZADA el {date.today().isoformat()}: {cfg['motivo']}")
        p.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        out.append(f"{ticker}: {cfg['campo']} reemplazado -> {cfg['nueva'][-3:]}")
    return out


def rellena_tags_antiguos(ticker: str) -> list:
    return [linea
            for cfg in TAGS_ANTIGUOS.get(ticker, [])
            for linea in _rellena_bloque(ticker, cfg)]


def _rellena_bloque(ticker: str, cfg: dict) -> list:
    p = RAW / f"{ticker}_{cfg['estado']}.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    # La marca de idempotencia va POR CAMPO, no por bloque. Si fuese por bloque, añadir mas
    # tarde un campo nuevo a un fichero ya procesado quedaria bloqueado en silencio, que es
    # justo lo que paso al recuperar las inversiones a corto de COP despues de la deuda.
    hechos = set(d.get("homogeneizado", {}).get("tags_antiguos", []))
    anios = [f[:4] for f in d["fiscal_dates"]]
    out, nuevos = [], []

    for campo, porano in cfg["valores"].items():
        if campo in hechos:
            out.append(f"{ticker}: {campo} ya rellenado, no se toca")
            continue
        fila = d["rows"][campo]
        for anio, val in porano.items():
            i = anios.index(anio)
            assert fila[i] is None, (
                f"{ticker} {campo} {anio}: ya hay un valor de la SEC ({fila[i]}), no se pisa")
            fila[i] = val
            out.append(f"{ticker}: {campo} {anio} = {val}")
        nuevos.append(campo)

    if not nuevos:
        return out
    d.setdefault("homogeneizado", {})["tags_antiguos"] = sorted(hechos | set(nuevos))
    d.setdefault("avisos", []).append(
        f"Rellenado el {date.today().isoformat()} ({', '.join(nuevos)}) desde un tag renombrado "
        f"o leido por otra via: {cfg['motivo']}")
    p.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


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
                                     | set(SIGNOS) | set(DISCONTINUIDADES)
                                     | set(TAGS_ANTIGUOS) | set(SERIES_REEMPLAZADAS))
    for t in tickers:
        for linea in (marca_discontinuidad(t) + normaliza_signos(t) + aplica_split(t)
                      + deriva_pasivo(t) + aplica_ceros(t) + rellena_tags_antiguos(t)
                      + reemplaza_series(t)):
            print(" ", linea)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
