#!/usr/bin/env python3
"""
Extracciones de la SEC del 6-sep-2026: UBER, ISRG y NVDA, mas los precios de
cierre por ejercicio para calcular el P/E historico.

HOMOGENEIZACION DE SPLITS. Los precios vienen ya ajustados por splits a la base
actual; el BPA y las acciones que publica la SEC estan en la base vigente en
cada filing. Para que precio/BPA signifique algo hay que llevarlos a la misma
base. Los factores se aplican aqui, y el control es BPA x acciones ~= beneficio.
  ISRG: 3:1 en oct-2017 y 3:1 en oct-2021. 2016-2020 llegan con el de 2017 ya
        incorporado pero no el de 2021 -> BPA /3, acciones x3.
  NVDA: 4:1 en jul-2021 y 10:1 en jun-2024. Conviven TRES bases porque cada
        10-K solo reexpresa los tres ejercicios de su ventana comparativa:
        FY2017-19 base original (40), FY2020-22 tras el 4:1 (10), FY2023-26 actual.
  MSFT, META y UBER: sin splits en la ventana.
"""
import json, pathlib

d = pathlib.Path(__file__).resolve().parent.parent / "fundamentals" / "raw"
d.mkdir(parents=True, exist_ok=True)
UD = ["2016-12-31","2017-12-31","2018-12-31","2019-12-31","2020-12-31","2021-12-31","2022-12-31","2023-12-31","2024-12-31","2025-12-31"]
ND = ["2017-01-29","2018-01-28","2019-01-27","2020-01-26","2021-01-31","2022-01-30","2023-01-29","2024-01-28","2025-01-26","2026-01-25"]
N = [None]*10

def ajusta(serie, factores, op):
    return [None if v is None else (round(v/f, 6) if op == "div" else round(v*f))
            for v, f in zip(serie, factores)]

ISRG_F = [3,3,3,3,3,1,1,1,1,1]
isrg_eps_pub = [6.26,5.77,9.49,11.54,8.82,4.66,3.65,5.03,6.42,7.87]
isrg_sh_pub  = [118,116,119,120,120,366,362,357,362,363]
NVDA_F = [40,40,40,10,10,10,1,1,1,1]
nvda_eps_pub = [2.57,4.82,6.63,1.13,1.73,3.85,0.17,1.19,2.94,4.90]
nvda_sh_pub  = [649,632,625,2472,2510,2535,25070,24940,24804,24514]

DATA = {
"UBER_is": {"ticker":"UBER","fiscal_dates":UD,"rows":{
 "revenue":[None,7932,10433,13000,11139,17455,31877,37281,43978,52017],
 "cogs":N,"gross_profit":N,
 "operating_income":[None,-4080,-3033,-8596,-4863,-3834,-1832,1110,2799,5565],
 "interest_expense":[None,-479,-648,-559,-458,-483,-565,-633,-523,-440],
 "income_tax":[None,542,-283,-45,192,492,181,-213,5758,4346],
 "net_income":[None,-4033,997,-8506,-6768,-496,-9141,1887,9856,10053],
 "eps_diluted":[None,-9.46,0.00,-6.81,-3.86,-0.29,-4.65,0.87,4.56,4.73],
 "diluted_shares":[None,426,479,1248,1753,1896,1975,2092,2151,2120],
 "rd_expense":[None,1201,1505,4836,2205,2054,2798,3164,3109,3402]},
 "avisos":["2016 sin hechos XBRL: Uber salio a bolsa en mayo de 2019 y 2016 solo figura en el S-1, que no esta en companyconcept. Ausencia esperada.",
  "Coste de ventas y beneficio bruto vacios los diez ejercicios: los tres tags dan 404 porque Uber usa una extension propia. El margen bruto sale n.d.",
  "EL IMPUESTO DE 2024 Y 2025 ES UN INGRESO, NO UN GASTO (+5.758 y +4.346), por liberacion de provision fiscal. Es el motor del salto del beneficio de 2024. El signo positivo es intencionado.",
  "El BPA no cuadra con beneficio/acciones en 2018, 2021 y 2023 (preferentes pre-IPO y ajustes del numerador atribuible al comun). No se ha forzado.",
  "Ventas de 2018 y 2019 reexpresadas a la baja en 10-K posteriores (2018 de 11.270 a 10.433; 2019 de 14.147 a 13.000)."]},
"UBER_bs": {"ticker":"UBER","fiscal_dates":UD,"rows":{
 "cash":[None,4393,6406,10873,5647,4295,4208,4680,5893,7105],
 "short_term_investments":[None,None,0,440,1180,0,103,727,1084,528],
 "total_current_assets":[None,None,8658,13925,9882,8819,9249,11297,12245,13993],
 "total_assets":[None,None,23988,31761,33252,38774,32109,38699,51244,61802],
 "total_current_liabilities":[None,None,4259,5639,6865,9024,8853,9454,11476,12320],
 "total_liabilities":[None,None,17196,16578,19498,23425,23605,26017,28768,33719],
 "total_equity":[None,-8557,-7385,14190,12266,14458,7340,11249,21558,27041],
 "short_term_borrowings":[None,None,None,None,None,None,None,None,None,0],
 "current_portion_ltd":[None,None,27,27,27,27,27,25,1150,0],
 "long_term_debt":[None,None,6869,5707,7560,9276,9265,9459,8347,10521],
 "finance_lease_current":[None,None,None,165,177,191,115,156,136,138],
 "finance_lease_noncurrent":[None,None,None,143,120,43,284,322,174,84],
 "operating_lease_current":[None,None,None,196,175,185,201,190,175,169],
 "operating_lease_noncurrent":[None,None,None,1523,1544,1644,1673,1550,1454,1390]},
 "avisos":["El balance NO cuadra como Activo = Pasivo + Patrimonio, y es correcto: Uber tiene preferentes convertibles y minoritarios redimibles en 'mezzanine equity', fuera del pasivo y del patrimonio. En 2018 la diferencia es de ~14.177 millones.",
  "Fondos propios NEGATIVOS en 2017 y 2018 (-8.557 y -7.385): dato real de la etapa pre-IPO. El ROE y la deuda/fondos propios de esos anos salen n.d. porque no significan nada con patrimonio negativo.",
  "Deuda a corto sin dato salvo 2025 (0)."]},
"UBER_cf": {"ticker":"UBER","fiscal_dates":UD,"rows":{
 "cfo":[None,-1418,-1541,-4321,-2745,-445,642,3585,7137,10099],
 "capex":[None,-821,-558,-588,-616,-298,-252,-223,-242,-336],
 "depreciation_amortization":[None,510,426,472,575,902,947,823,711,719],
 "stock_based_compensation":[None,124,170,4596,827,1168,1793,1935,1796,1826],
 "buybacks":[None,None,None,None,None,None,0,0,1252,6523],
 "dividends_paid":N,
 "cash_taxes_paid":[None,153,289,133,82,87,175,234,324,345]},
 "avisos":["El flujo de explotacion fue NEGATIVO cinco ejercicios seguidos, de 2017 a 2021. Dato real.",
  "Uber no paga dividendo. Las recompras empiezan en 2024."]},
"ISRG_is": {"ticker":"ISRG","fiscal_dates":UD,"rows":{
 "revenue":[2707,3138,3724,4479,4358,5710,6222,7124,8352,10065],
 "cogs":[814,936,1120,1368,1497,1752,2026,2395,2718,3422],
 "gross_profit":[1893,2202,2604,3110,2861,3959,4196,4730,5634,6642],
 "operating_income":[950,1063,1199,1375,1050,1821,1577,1767,2349,2946],
 "interest_expense":N,
 "income_tax":[-247,-434,-155,-120,-140,-162,-262,-142,-336,-435],
 "net_income":[738,671,1128,1379,1061,1705,1322,1798,2323,2856],
 "eps_diluted":ajusta(isrg_eps_pub, ISRG_F, "div"),
 "diluted_shares":ajusta(isrg_sh_pub, ISRG_F, "mul"),
 "rd_expense":[240,329,418,557,595,671,879,999,1145,1312]},
 "avisos":["BPA y acciones de 2016-2020 homogeneizados por el split 3:1 de octubre de 2021 (BPA /3, acciones x3). La SEC los publica como "+str(isrg_eps_pub)+" y "+str(isrg_sh_pub)+".",
  "El subagente detecto un SEGUNDO split 3:1 durante 2017 que no estaba en el encargo: el 10-K original de 2016 daba 39,3 millones de acciones y 18,73 de BPA, y los filings posteriores lo reexpresan a ~118 millones y ~6,26. La regla del 'filed' mas reciente ya recoge ese ajuste.",
  "Sin gasto financiero los diez ejercicios: los tres tags dan 404, Intuitive Surgical no tiene deuda. La cobertura de intereses sale n.d. porque no hay intereses que cubrir.",
  "Beneficio neto = NetIncomeLoss, atribuible a la matriz."]},
"ISRG_bs": {"ticker":"ISRG","fiscal_dates":UD,"rows":{
 "cash":[1037,648,858,1168,1623,1291,1581,2750,2027,3368],
 "short_term_investments":[1518,1312,2205,2054,3489,2913,2537,2473,1986,2567],
 "total_current_assets":[3250,2809,4333,4663,6626,5845,6253,7888,7111,9780],
 "total_assets":[6487,5777,7847,9733,11169,13555,12974,15442,18743,20459],
 "total_current_liabilities":[597,663,821,1030,965,1150,1422,1659,1745,2006],
 "total_liabilities":[709,996,1159,1449,1410,1604,1861,2044,2214,2517],
 "total_equity":[5778,4779,6679,8264,9732,11901,11042,13308,16434,17824],
 "short_term_borrowings":N,"current_portion_ltd":N,"long_term_debt":N,
 "finance_lease_current":N,"finance_lease_noncurrent":N,
 "operating_lease_current":[None,None,None,8,22,20,24,25,34,39],
 "operating_lease_noncurrent":[None,None,None,69,58,67,70,65,113,132]},
 "avisos":["SIN DEUDA FINANCIERA los diez ejercicios: los cuatro tags dan 404. Ausencia real confirmada. La unica deuda del calculo son los arrendamientos operativos desde 2019.",
  "El balance cuadra: la diferencia entre Activo y Pasivo + Patrimonio de la matriz coincide ano a ano con los minoritarios (de 1,6 millones en 2017 a 118 en 2025).",
  "ANCLA FALLIDA MIA: di 17.980 millones de activo a cierre de 2024 y el dato real es 18.743 (+4,2%). El subagente no lo ajusto, lo reporto y verifico que cuadra. El error era de la ancla."]},
"ISRG_cf": {"ticker":"ISRG","fiscal_dates":UD,"rows":{
 "cfo":[1043,1144,1170,1598,1485,2089,1491,1814,2415,3031],
 "capex":[-54,-191,-187,-426,-342,-354,-532,-1064,-1111,-540],
 "depreciation_amortization":[71,82,106,157,221,280,326,382,439,600],
 "stock_based_compensation":[178,209,261,336,395,449,513,593,677,788],
 "buybacks":[43,2274,0,270,134,0,2607,416,0,2295],
 "dividends_paid":N,
 "cash_taxes_paid":[138,148,179,159,34,180,444,448,467,538]},
 "avisos":["Flujo de explotacion positivo los diez ejercicios.",
  "Amortizacion del tag Depreciation: los dos preferentes dan 404. Puede no incluir intangibles, asi que el EBITDA queda algo infravalorado.",
  "ANCLA FALLIDA MIA: di 2.510 millones de flujo para 2024 y el real es 2.415 (-3,8%). Verificado en dos filings.",
  "Intuitive Surgical no ha pagado dividendo nunca."]},
"NVDA_is": {"ticker":"NVDA","fiscal_dates":ND,"rows":{
 "revenue":[6910,9714,11716,10918,16675,26914,26974,60922,130497,215938],
 "cogs":[2847,3892,4545,4150,6279,9439,11618,16621,32639,62475],
 "gross_profit":[4063,5822,7171,6768,10396,17475,15356,44301,97858,153463],
 "operating_income":[1934,3210,3804,2846,4532,10041,4224,32972,81453,130387],
 "interest_expense":[-58,-61,-58,-52,-184,-236,-262,-257,-247,-259],
 "income_tax":[-239,-149,245,-174,-77,-189,187,-4058,-11146,-21383],
 "net_income":[1666,3047,4141,2796,4332,9752,4368,29760,72880,120067],
 "eps_diluted":ajusta(nvda_eps_pub, NVDA_F, "div"),
 "diluted_shares":ajusta(nvda_sh_pub, NVDA_F, "mul"),
 "rd_expense":[1463,1797,2376,2829,3924,5268,7339,8675,12914,18497]},
 "avisos":["Ejercicio cerrado el ultimo domingo de enero: las fechas no son un dia fijo.",
  "BPA y acciones homogeneizados a la base actual desde TRES bases distintas (factores 40, 10 y 1). La SEC solo reexpresa los tres ejercicios de la ventana comparativa de cada 10-K. Publicados eran "+str(nvda_eps_pub)+" y "+str(nvda_sh_pub)+".",
  "El impuesto de FY2019 y FY2023 fue un INGRESO fiscal (+245 y +187), no un gasto."]},
"NVDA_bs": {"ticker":"NVDA","fiscal_dates":ND,"rows":{
 "cash":[1766,4002,782,10896,847,1990,3389,7280,8589,10605],
 "short_term_investments":[5032,3106,6640,1,10714,19218,9907,18704,34621,None],
 "total_current_assets":[8536,9255,10557,13690,16055,28829,23073,44345,80126,125605],
 "total_assets":[9841,11241,13292,17315,28791,44187,41182,65728,111601,206803],
 "total_current_liabilities":[1788,1153,1329,1784,3925,4335,6563,10631,18047,32163],
 "total_liabilities":[4048,3770,3950,5111,11898,17575,19081,22750,32274,49510],
 "total_equity":[5762,7471,9342,12204,16893,26612,22101,42978,79327,157293],
 "short_term_borrowings":[None,None,0,0,0,None,None,0,0,None],
 "current_portion_ltd":[None,None,None,0,999,0,1250,1250,0,999],
 "long_term_debt":[1983,1985,1988,1991,5964,10946,9703,8459,8463,7469],
 "finance_lease_current":N,"finance_lease_noncurrent":N,
 "operating_lease_current":[None,None,None,91,121,144,176,228,288,372],
 "operating_lease_noncurrent":[None,None,None,561,634,741,902,1119,1519,2572]},
 "avisos":["FALTA EL DATO MAS IMPORTANTE: las inversiones a corto de FY2026 (cierre 25-ene-2026) no existen bajo ninguno de los tres tags; el ultimo hecho de MarketableSecuritiesCurrent es de octubre de 2025 (49.122 millones). Verificado directamente. Consecuencia: caja total, deuda neta y ROIC de FY2026 salen n.d. Probable cambio de etiqueta en el 10-K de FY2026.",
  "El balance de FY2017 no cuadra por 31 millones (0,32%). Verificado dos veces: es una inconsistencia del propio filing. Los otros nueve cuadran exactos.",
  "Deuda a largo de FY2017-2019 del tag LongTermDebt (total) porque LongTermDebtNoncurrent no existe esos anos.",
  "NVIDIA no etiqueta arrendamientos financieros; solo operativos desde FY2020."]},
"NVDA_cf": {"ticker":"NVDA","fiscal_dates":ND,"rows":{
 "cfo":[1672,3502,3743,4761,5822,9108,5641,28090,64089,102718],
 "capex":[None,None,None,None,None,-976,-1833,-1069,-3236,-6042],
 "depreciation_amortization":[118,144,233,381,1098,1174,1544,1508,1864,2843],
 "stock_based_compensation":[247,391,557,844,1397,2004,2709,3549,4737,6386],
 "buybacks":[739,909,1579,0,0,0,10039,9533,33706,40086],
 "dividends_paid":[261,341,371,390,395,399,398,395,834,974],
 "cash_taxes_paid":[14,22,61,176,249,396,1404,6549,15118,20288]},
 "avisos":["SIN CAPEX EN FY2017-FY2021: ninguno de los dos tags tiene hecho anual esos ejercicios. El flujo de caja libre solo existe de FY2022 en adelante, cinco ejercicios, asi que el CAGR del FCF a 5 anos sale n.d.",
  "Amortizacion de FY2017-2019 del tag Depreciation (solo inmovilizado); de FY2020 en adelante es el tag completo. Los tres primeros anos no son homogeneos.",
  "Flujo de explotacion positivo los diez ejercicios."]},
}
for name, payload in DATA.items():
    assert all(len(v) == 10 for v in payload["rows"].values()), name
    (d / f"{name}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1)+"\n", encoding="utf-8")

PRECIOS = {
 "MSFT":[None,68.93,98.61,133.96,203.51,270.90,256.83,340.54,446.95,497.41],
 "META":[115.05,176.46,131.09,205.25,273.16,336.35,120.34,353.96,585.51,660.09],
 "UBER":[None,None,None,29.74,51.00,41.93,24.73,61.57,60.32,81.71],
 "ISRG":[70.463,121.647,159.64,197.05,272.70,359.30,265.35,337.36,521.96,566.36],
 "NVDA":N}
(d/"_precios.json").write_text(json.dumps({
 "fuente":"API de stockanalysis.com, campo 'c' (ajustado solo por splits, nunca por dividendos)",
 "obtenido":"2026-09-06","precios":PRECIOS,
 "avisos":["MSFT 30-jun-2016: la ventana de 10 anos en periodo mensual no llega hasta ahi.",
  "NVDA: los diez precios sin obtener, el limite de sesion de WebFetch se agoto a mitad de la consulta.",
  "UBER 2016-2018: no cotizaba, salio a bolsa el 10-may-2019.",
  "Fechas desplazadas al ultimo dia habil anterior cuando el cierre caia en fin de semana."]},
 ensure_ascii=False, indent=1)+"\n", encoding="utf-8")

print("9 ficheros crudos + precios escritos")
print("ISRG BPA homogeneizado 2016-2020:", ajusta(isrg_eps_pub, ISRG_F, "div")[:5])
print("NVDA BPA homogeneizado:", ajusta(nvda_eps_pub, NVDA_F, "div"))
print("NVDA acciones homogeneizadas:", ajusta(nvda_sh_pub, NVDA_F, "mul"))
