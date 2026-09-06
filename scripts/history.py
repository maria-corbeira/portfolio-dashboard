#!/usr/bin/env python3
"""
Historico de cierres diarios y lo que se calcula a partir de el.

prices_history.json guarda, por ticker, una lista de [fecha, cierre]. Lo alimenta
fetch_prices.py en cada pasada: un punto por sesion, el ultimo de la jornada gana.
Se recorta a MAX_SESIONES para que el fichero no crezca sin fin.

De ese historico salen tres cosas que antes no se podian calcular:
  - variacion a 1 dia y a 5 sesiones, para el aviso de movimiento fuerte
  - RSI de 14 sesiones
  - media movil de 200 sesiones
Las tres devuelven None mientras no haya sesiones suficientes. Nunca se rellenan
con un valor aproximado: un RSI calculado sobre 20 sesiones no es un RSI de 14.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

MAX_SESIONES = 420          # algo mas de 200 sesiones + margen
UMBRAL_FUERTE = 5.0         # porcentaje que dispara el aviso


def carga(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
        return d.get("series", {}) if isinstance(d, dict) else {}
    except Exception:
        return {}


def actualiza(series: dict, precios: dict, fecha: str | None = None) -> dict:
    """Anade el cierre de hoy. Si ya hay un punto de la misma fecha, lo sustituye:
    el Action corre cada 15 min y solo interesa el ultimo de cada sesion."""
    hoy = fecha or datetime.now(timezone.utc).date().isoformat()
    for t, q in precios.items():
        p = q.get("price")
        if p is None:
            continue
        serie = series.setdefault(t, [])
        if serie and serie[-1][0] == hoy:
            serie[-1][1] = p
        else:
            serie.append([hoy, p])
        if len(serie) > MAX_SESIONES:
            del serie[:len(serie) - MAX_SESIONES]
    return series


def guarda(path: Path, series: dict) -> None:
    path.write_text(json.dumps({
        "_nota": ("Cierres diarios por ticker, [fecha, precio]. Lo escribe "
                  "scripts/fetch_prices.py. Sirve para las variaciones a 1 y 5 "
                  "sesiones, el RSI de 14 y la media de 200."),
        "actualizado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sesiones_max": MAX_SESIONES,
        "series": series,
    }, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def variacion(serie: list, sesiones: int):
    if len(serie) < sesiones + 1:
        return None
    antes, ahora = serie[-sesiones - 1][1], serie[-1][1]
    if not antes:
        return None
    return round((ahora / antes - 1) * 100, 2)


def rsi(serie: list, periodo: int = 14):
    """RSI de Wilder. None si no hay al menos periodo+1 cierres."""
    if len(serie) < periodo + 1:
        return None
    cierres = [p for _, p in serie]
    ganancias, perdidas = [], []
    for a, b in zip(cierres[-periodo - 1:-1], cierres[-periodo:]):
        d = b - a
        ganancias.append(max(d, 0.0))
        perdidas.append(max(-d, 0.0))
    mg = sum(ganancias) / periodo
    mp = sum(perdidas) / periodo
    if mp == 0:
        return 100.0 if mg > 0 else 50.0
    rs = mg / mp
    return round(100 - 100 / (1 + rs), 1)


def media(serie: list, sesiones: int = 200):
    if len(serie) < sesiones:
        return None
    return round(sum(p for _, p in serie[-sesiones:]) / sesiones, 2)


def indicadores(series: dict, precios: dict) -> dict:
    """Devuelve, por ticker, lo que el dashboard necesita para Timing y avisos."""
    out = {}
    for t, serie in series.items():
        actual = (precios.get(t) or {}).get("price")
        m200 = media(serie, 200)
        out[t] = {
            "sesiones": len(serie),
            "var_1d": variacion(serie, 1),
            "var_5d": variacion(serie, 5),
            "rsi_14": rsi(serie, 14),
            "ma_200": m200,
            "vs_ma200": (round((actual / m200 - 1) * 100, 1)
                         if (actual and m200) else None),
        }
    return out


def fuertes(indic: dict, umbral: float = UMBRAL_FUERTE) -> list:
    """Movimientos que superan el umbral en 1 dia o en 5 sesiones."""
    out = []
    for t, d in indic.items():
        for campo, etiqueta in (("var_1d", "1 día"), ("var_5d", "5 sesiones")):
            v = d.get(campo)
            if v is not None and abs(v) >= umbral:
                out.append({"ticker": t, "ventana": etiqueta, "pct": v})
    out.sort(key=lambda x: abs(x["pct"]), reverse=True)
    return out
