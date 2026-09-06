#!/usr/bin/env python3
"""Escribe en fundamentals/raw/ las seis extracciones de la SEC del 5-sep-2026.
Cada fichero conserva los avisos del extractor: son la trazabilidad del dato."""
import json, pathlib
d = pathlib.Path(__file__).resolve().parent.parent / "fundamentals" / "raw"
d.mkdir(parents=True, exist_ok=True)
MS = ["2016-06-30","2017-06-30","2018-06-30","2019-06-30","2020-06-30","2021-06-30","2022-06-30","2023-06-30","2024-06-30","2025-06-30"]
MT = ["2016-12-31","2017-12-31","2018-12-31","2019-12-31","2020-12-31","2021-12-31","2022-12-31","2023-12-31","2024-12-31","2025-12-31"]
N = [None]*10
DATA = {
"MSFT_is": {"ticker":"MSFT","fiscal_dates":MS,"rows":{
 "revenue":[91154,96571,110360,125843,143015,168088,198270,211915,245122,281724],
 "cogs":[32780,34261,38353,42910,46078,52232,62650,65863,74114,87831],
 "gross_profit":[58374,62310,72007,82933,96937,115856,135620,146052,171008,193893],
 "operating_income":[26078,29025,35058,42959,52959,69916,83383,88523,109433,128528],
 "interest_expense":[-1243,-2222,-2733,-2686,-2591,-2346,-2063,-1968,-2935,-2385],
 "income_tax":[-5100,-4412,-19903,-4448,-8755,-9831,-10978,-16950,-19651,-21795],
 "net_income":[20539,25489,16571,39240,44281,61271,72738,72361,88136,101832],
 "eps_diluted":[2.56,3.25,2.13,5.06,5.76,8.05,9.65,9.68,11.80,13.64],
 "diluted_shares":[8013,7832,7794,7753,7683,7608,7540,7472,7469,7465],
 "rd_expense":[11988,13037,14726,16876,19269,20716,24512,27195,29510,32488]},
 "avisos":["FY2016 y FY2017 son cifras reexpresadas por la adopcion retrospectiva de ASC 606 (10-K de FY2018): las ventas de FY2016 pasaron de 85.320 a 91.154 y las de FY2017 de 89.950 a 96.571. Se usan las reexpresadas, conforme a la regla del 'filed' mas reciente.",
  "El impuesto de FY2018 (19.903) es anormalmente alto por el cargo unico de repatriacion de la reforma fiscal TCJA. No es un error de extraccion.",
  "El gasto financiero de FY2025 procede de InterestExpenseNonoperating; InterestExpense dejo de publicarse ese ejercicio."]},
"MSFT_bs": {"ticker":"MSFT","fiscal_dates":MS,"rows":{
 "cash":[6510,7663,11946,11356,13576,14224,13931,34704,18315,30242],
 "short_term_investments":[None,None,121822,122463,122951,116110,90826,76558,57228,64323],
 "total_current_assets":[139660,162696,169662,175552,181915,184406,169684,184257,159734,191131],
 "total_assets":[193468,250312,258848,286556,301311,333779,364840,411976,512163,619003],
 "total_current_liabilities":[59357,55745,58488,69420,72310,88657,95082,104149,125286,141218],
 "total_liabilities":[121471,162601,176130,184226,183007,191791,198298,205753,243686,275524],
 "total_equity":[71997,87711,82718,102330,118304,141988,166542,206223,268477,343479],
 "short_term_borrowings":[12904,9072,0,0,None,None,None,0,6693,0],
 "current_portion_ltd":[0,1049,3998,5516,3749,8072,2749,5247,2249,2999],
 "long_term_debt":[40783,76073,72242,66662,59578,50074,47032,41990,42688,40152],
 "finance_lease_current":N,
 "finance_lease_noncurrent":[None,None,None,6574,9496,12541,14902,17067,27145,46172],
 "operating_lease_current":N,
 "operating_lease_noncurrent":[None,5372,5568,6188,7671,9629,11489,12728,15497,17437]},
 "avisos":["El balance cuadra exacto (Activo = Pasivo + Patrimonio) en los 10 ejercicios.",
  "Microsoft no desglosa el arrendamiento financiero en corriente y no corriente: los dos tags dan 404. Se usa el agregado FinanceLeaseLiability colocado entero en la fila no corriente; el total de deuda es correcto, el reparto por plazo no.",
  "OperatingLeaseLiabilityCurrent da 404 en Microsoft: la deuda total queda infravalorada en el arrendamiento operativo corriente, del orden de unos pocos miles de millones. No se estima.",
  "Sin dato de deuda a corto en 2020-2022: ni ShortTermBorrowings ni CommercialPaper tienen entradas. En 2019 y 2023 se publica 0 explicito, asi que probablemente tambien fuera 0, pero no se asume.",
  "Sin dato de inversiones a corto en 2016 y 2017: la caja total y la deuda neta de esos dos ejercicios salen vacias."]},
"MSFT_cf": {"ticker":"MSFT","fiscal_dates":MS,"rows":{
 "cfo":[33325,39507,43884,52185,60675,76740,89035,87582,118548,136162],
 "capex":[-8343,-8129,-11632,-13925,-15441,-20622,-23886,-28107,-44477,-64551],
 "depreciation_amortization":N,
 "stock_based_compensation":[2668,3266,3940,4652,5289,6118,7502,9611,10734,11974],
 "buybacks":[15969,11788,10721,19543,22968,27385,32696,22245,17254,18420],
 "dividends_paid":[11006,11845,12699,13811,15137,16521,18135,19800,21771,24082],
 "cash_taxes_paid":[3900,2400,5500,8400,12500,13400,16000,23100,23400,28700]},
 "avisos":["AMORTIZACION DELIBERADAMENTE VACIA. DepreciationDepletionAndAmortization y DepreciationAmortizationAndAccretionNet dan 404 en Microsoft, y el tag Depreciation solo recoge la del inmovilizado: valores redondeados a centenas de millon y no monotonos (10.700 en FY2020 frente a 9.300 en FY2021). Usarlo falsearia el EBITDA. Consecuencia: EBITDA y Deuda neta/EBITDA salen n.d. en Microsoft hasta consultar la etiqueta propia de la empresa."]},
"META_is": {"ticker":"META","fiscal_dates":MT,"rows":{
 "revenue":[27638,40653,55838,70697,85965,117929,116609,134902,164501,200966],
 "cogs":[3789,5454,9355,12770,16692,22649,25249,25959,30161,36175],
 "gross_profit":N,
 "operating_income":[12427,20203,24913,23986,32671,46753,28944,46751,69380,83276],
 "interest_expense":[-10,-6,-9,-20,None,-23,-185,-446,-715,-1165],
 "income_tax":[-2301,-4660,-3249,-6327,-4034,-7914,-5619,-8330,-8303,-25474],
 "net_income":[10217,15934,22112,18485,29146,39370,23200,39098,62360,60458],
 "eps_diluted":[3.49,5.39,7.57,6.43,10.09,13.77,8.59,14.87,23.86,23.49],
 "diluted_shares":[2925,2956,2921,2876,2888,2859,2702,2629,2614,2574],
 "rd_expense":[5919,7754,10273,13600,18447,24655,35338,38483,43873,57372]},
 "avisos":["Meta no etiqueta GrossProfit en XBRL (404 los diez ejercicios): el beneficio bruto se deriva como ventas menos coste de ventas, aritmetica sobre datos publicados.",
  "Sin gasto financiero en 2020 bajo ninguno de los tres tags. Meta no tuvo deuda en bonos hasta agosto de 2022: las cifras de 2016-2021 (entre 6 y 23 millones) son partidas menores.",
  "El impuesto de FY2025 (25.474) triplica el de FY2024 (8.303) y es lo que hace caer el beneficio neto pese a crecer las ventas un 22%. La causa concreta no se ha verificado en el texto del 10-K."]},
"META_bs": {"ticker":"META","fiscal_dates":MT,"rows":{
 "cash":[8903,8079,10019,19079,17576,16601,14681,41862,43889,35873],
 "short_term_investments":[20546,33632,31095,35776,44378,31397,26057,23541,33926,45719],
 "total_current_assets":[34401,48563,50480,66225,75670,66666,59549,85365,100045,108722],
 "total_assets":[64961,84524,97334,133376,159316,165987,185727,229623,276054,366021],
 "total_current_liabilities":[2875,3760,7017,15053,14981,21135,27026,31960,33596,41836],
 "total_liabilities":[5767,10177,13207,32322,31026,41108,60014,76455,93417,148778],
 "total_equity":[59194,74347,84127,101054,128290,124879,125713,153168,182637,217243],
 "short_term_borrowings":N,"current_portion_ltd":N,
 "long_term_debt":[None,None,None,None,None,None,9923,18385,28826,58744],
 "finance_lease_current":[None,None,None,55,54,75,129,90,76,308],
 "finance_lease_noncurrent":[None,None,418,None,469,506,558,600,633,876],
 "operating_lease_current":[None,None,None,800,1023,1127,1367,1623,1942,2213],
 "operating_lease_noncurrent":[None,None,0,9524,9631,12746,15301,17226,18292,22940]},
 "avisos":["El balance cuadra exacto (Activo = Pasivo + Patrimonio) en los 10 ejercicios.",
  "Meta no usa ShortTermBorrowings, CommercialPaper ni LongTermDebtCurrent (404 los diez anos): no tiene deuda financiera a corto plazo etiquetada.",
  "Sin deuda a largo en 2016-2021 porque Meta no emitio bonos hasta agosto de 2022.",
  "Sin hecho puntual de arrendamiento financiero no corriente a 31-12-2019 bajo ese tag: se deja vacio en vez de derivarlo del total.",
  "El 0 de arrendamiento operativo no corriente a 31-12-2018 es un dato real, no una ausencia: bajo ASC 840 los arrendamientos operativos no se reconocian en balance."]},
"META_cf": {"ticker":"META","fiscal_dates":MT,"rows":{
 "cfo":[16108,24216,29274,36314,38747,57683,50475,71113,91328,115800],
 "capex":[-4491,-6733,-13915,-15102,-15163,-18690,-31186,-27045,-37256,-69691],
 "depreciation_amortization":[2342,3025,4315,5741,6862,7967,8686,11178,15498,18616],
 "stock_based_compensation":[3218,3723,4152,4836,6536,9164,11992,14027,16690,20427],
 "buybacks":[0,1976,12879,4202,6272,44537,27956,19774,30125,26248],
 "dividends_paid":[None,None,None,None,None,None,None,None,5072,5324],
 "cash_taxes_paid":[1210,2117,3762,5182,4229,8525,6407,6607,10554,7578]},
 "avisos":["El capex esta reexpresado en varios ejercicios; se usa el 'filed' mas reciente (FY2022 de 31.431 a 31.186; FY2023 de 27.266 a 27.045).",
  "Meta no pago dividendo hasta 2024: en 2016-2023 es ausencia real, no cero."]},
}
for name, payload in DATA.items():
    assert all(len(v) == 10 for v in payload["rows"].values()), name
    (d / f"{name}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(f"{len(DATA)} ficheros crudos escritos, 10 valores por fila en todos")
