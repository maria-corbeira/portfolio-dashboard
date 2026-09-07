#!/usr/bin/env python3
"""
Descarga noticias de los tickers de index.html y del mercado, y escribe news.json.
Lo ejecuta .github/workflows/news.yml.

Fuentes: RSS publico, sin clave ni cuenta. Cada fuente se intenta por separado y
su resultado queda registrado en `fuentes_estado`: si una se cae, las demas siguen.

AVISO SOBRE LA CLASIFICACION. La etiqueta de cada noticia (hecho, rumor, analista,
resultados) se decide con reglas sobre el titular, no leyendo la noticia. Es una
ayuda para ordenar la vista, NO una verificacion. Un titular marcado como "hecho"
puede seguir siendo un rumor mal titulado. La unica etiqueta con garantia es
"filing", que viene de la SEC.
"""
import json, re, sys, time, html, urllib.request, urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
OUT = ROOT / "news.json"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
POR_TICKER = 5          # cuantas novedades guardar por accion
MAX_MERCADO = 12
DIAS_MAX = 45           # descarta lo mas viejo que esto
DIAS_CALENDARIO = 45    # cuantos dias hacia delante se busca fecha de resultados

ESTADO, ERRORES = {}, []

# --- clasificacion heuristica por titular ------------------------------------
# El orden importa: la primera que casa, gana.
REGLAS = [
    ("resultados", r"\b(earnings|q[1-4]\s|quarterly result|reports? (q[1-4]|fourth|third|second|first)|"
                   r"beats?|misses?|guidance|outlook|revenue (rose|fell|jumps?|climbs?)|"
                   r"resultados|beneficio|ingresos)\b"),
    ("analista", r"\b(price target|upgrade[sd]?|downgrade[sd]?|initiat\w+ coverage|"
                 r"raises? (its )?target|cuts? (its )?target|overweight|underweight|"
                 r"buy rating|sell rating|neutral rating|analyst)\b"),
    ("rumor", r"\b(rumou?r|reportedly|sources? say|people familiar|is said to|"
              r"could|may|might|weighing|explores?|in talks|considering|"
              r"según fuentes|se rumorea|estudia|negocia)\b"),
    ("producto", r"\b(launch\w*|unveil\w*|announce[sd]? (the )?new|introduc\w+|"
                 r"debut\w*|releases?|rolls? out|lanza|presenta)\b"),
]
RUMOR_DURO = re.compile(r"\b(rumou?r|reportedly|sources? say|people familiar|is said to)\b", re.I)


def clasifica(titulo: str) -> str:
    t = titulo.lower()
    for etiqueta, patron in REGLAS:
        if re.search(patron, t, re.I):
            return etiqueta
    return "hecho"


def sin_confirmar(titulo: str) -> bool:
    return bool(RUMOR_DURO.search(titulo))


# --- utilidades ---------------------------------------------------------------
def get(url: str, tag: str, timeout: int = 20):
    for intento in range(3):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA, "Accept": "application/rss+xml,application/xml,text/xml,*/*"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                ESTADO[tag] = "ok"
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and intento < 2:
                time.sleep(3 * (intento + 1)); continue
            ESTADO[tag] = f"HTTP {e.code}"
            ERRORES.append(f"{tag}: HTTP {e.code}")
            return None
        except Exception as e:
            if intento < 2:
                time.sleep(2); continue
            ESTADO[tag] = type(e).__name__
            ERRORES.append(f"{tag}: {type(e).__name__}: {str(e)[:120]}")
            return None
    return None


def parse_rss(raw: bytes, fuente: str, tag: str) -> list:
    if not raw:
        return []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        ESTADO[tag] = f"XML mal formado: {str(e)[:60]}"
        return []
    out = []
    for it in root.iter("item"):
        t = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        fecha = (it.findtext("pubDate") or "").strip()
        if not t or not link:
            continue
        out.append({"title": html.unescape(t), "url": link,
                    "source": fuente, "published_raw": fecha})
    # Atom, por si alguna fuente lo usa
    ns = "{http://www.w3.org/2005/Atom}"
    for it in root.iter(f"{ns}entry"):
        t = (it.findtext(f"{ns}title") or "").strip()
        le = it.find(f"{ns}link")
        link = le.get("href") if le is not None else ""
        if not t or not link:
            continue
        out.append({"title": html.unescape(t), "url": link, "source": fuente,
                    "published_raw": (it.findtext(f"{ns}updated") or "").strip()})
    return out


def fecha_iso(s: str):
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z",
                "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%a, %d %b %Y %H:%M %z"):
        try:
            d = datetime.strptime(s, fmt)
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            return d.astimezone(timezone.utc)
        except (ValueError, TypeError):
            continue
    return None


def normaliza(titulo: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", titulo.lower()).strip()


def dedupe(items: list) -> list:
    vistos, out = set(), []
    for it in items:
        clave = normaliza(it["title"])[:70]
        if clave in vistos:
            continue
        vistos.add(clave)
        out.append(it)
    return out


def tickers_from_index() -> list:
    html_txt = INDEX.read_text(encoding="utf-8")
    bloque = html_txt[html_txt.index("const holdings"):html_txt.index("const watchlist")]
    seen, out = set(), []
    for t in re.findall(r'\bt:\s*"([A-Z][A-Z0-9.\-]{0,9})"', bloque):
        if t not in seen:
            seen.add(t); out.append(t)
    return out


# --- fuentes ------------------------------------------------------------------
# Yahoo Finance estuvo aqui como segunda fuente y se retiro el 6-sep-2026. Devolvio
# HTTP 429 en los 15 tickers, 15 de 15, en la primera pasada real del Action, igual que
# ya le habia pasado a fetch_prices.py: limita las IPs de GitHub Actions por volumen.
# No aporto ni una noticia (las 75 salieron de Google News) y costaba 15 peticiones que
# se reintentaban tres veces con esperas de 3 y 6 segundos: unos 135 segundos por pasada,
# cada 6 horas. Si algun dia se quiere recuperar, hay que comprobarlo antes con probe.yml
# y sabiendo que el probe ya dio verde a Yahoo una vez y en produccion siguio dando 429.
def noticias_ticker(t: str) -> list:
    items = []
    items += parse_rss(get(f"https://news.google.com/rss/search?q={t}+stock+when:30d"
                           "&hl=en-US&gl=US&ceid=US:en", f"google:{t}"), "Google News", f"google:{t}")
    return items


FUENTES_MERCADO = [
    ("MarketWatch", "https://feeds.content.dowjones.io/public/rss/mw_topstories", ["mercado"]),
    ("CNBC Mercados", "https://search.cnbc.com/rs/search/combinedcderpage.htm"
                      "?partnerId=wrss01&id=20910258", ["mercado"]),
    ("Reserva Federal", "https://www.federalreserve.gov/feeds/press_all.xml", ["macro", "politica"]),
    ("Google News · mercado", "https://news.google.com/rss/search?"
        "q=stock+market+OR+federal+reserve+OR+tariffs+when:3d&hl=en-US&gl=US&ceid=US:en",
        ["macro", "politica"]),
    ("Google News · IA y semis", "https://news.google.com/rss/search?"
        "q=(AI+capex+OR+data+center+spending+OR+semiconductor+export)+when:7d"
        "&hl=en-US&gl=US&ceid=US:en", ["capex-ia"]),
]


def noticias_mercado() -> list:
    out = []
    for nombre, url, tags in FUENTES_MERCADO:
        for it in parse_rss(get(url, f"mercado:{nombre}"), nombre, f"mercado:{nombre}"):
            it["tags"] = tags
            out.append(it)
        time.sleep(0.5)
    return out


def calendario_resultados(tickers: list) -> list:
    """Fechas de resultados, desde el calendario DIARIO de Nasdaq.

    Se consulta dia a dia `api.nasdaq.com/api/calendar/earnings?date=YYYY-MM-DD` y se
    guardan las filas cuyo simbolo este en la cartera. Es el unico endpoint de fechas que
    respondio en el probe del 7-sep-2026: `company/{t}/earnings-date` se retiro (404 en los
    15 tickers) y `quote/{t}/eps` responde 200 pero su JSON no trae ninguna fecha, que es
    por lo que el calendario llevaba semanas saliendo vacio.

    Se recorren solo dias habiles y se para en cuanto todos los tickers tienen fecha, asi
    que en temporada de resultados son pocas peticiones y fuera de ella son unas 30.

    Si nada responde, el calendario sale VACIO. Nunca se estima ni se interpola una fecha:
    una fecha de resultados inventada es peor que ninguna.
    """
    pendientes = {t.strip().upper() for t in tickers}
    out = []
    hoy = datetime.now(timezone.utc).date()
    for delta in range(DIAS_CALENDARIO):
        if not pendientes:
            break
        dia = hoy + timedelta(days=delta)
        if dia.weekday() >= 5:          # el calendario no publica sabados ni domingos
            continue
        raw = get(f"https://api.nasdaq.com/api/calendar/earnings?date={dia:%Y-%m-%d}",
                  f"cal:{dia:%Y-%m-%d}")
        if not raw:
            continue
        try:
            filas = (json.loads(raw).get("data") or {}).get("rows") or []
        except Exception as e:
            ERRORES.append(f"cal:{dia:%Y-%m-%d}: {type(e).__name__}")
            continue
        for f in filas:
            if not isinstance(f, dict):
                continue
            sim = str(f.get("symbol") or "").strip().upper()
            if sim not in pendientes:
                continue
            pendientes.discard(sim)
            limpia = lambda k: (str(f.get(k) or "").strip() or None)
            out.append({"ticker": sim,
                        # el frontend hace fecha_texto.slice(0,10) y exige ISO
                        "fecha_texto": dia.isoformat(),
                        "hora": limpia("time"),
                        "eps_estimado": limpia("epsForecast"),
                        "trimestre": limpia("fiscalQuarterEnding"),
                        "fuente": "nasdaq-calendar"})
        time.sleep(0.4)
    out.sort(key=lambda x: x["fecha_texto"])
    return out


# --- main ---------------------------------------------------------------------
def main() -> int:
    tickers = tickers_from_index()
    if not tickers:
        print("ERROR: no se encontro ningun ticker en index.html", file=sys.stderr)
        return 1
    print(f"{len(tickers)} tickers: {', '.join(tickers)}")
    limite = datetime.now(timezone.utc) - timedelta(days=DIAS_MAX)

    def prepara(items, n):
        salida = []
        for it in dedupe(items):
            d = fecha_iso(it.get("published_raw", ""))
            if d and d < limite:
                continue
            it["published"] = d.isoformat() if d else None
            it["kind"] = clasifica(it["title"])
            it["unconfirmed"] = sin_confirmar(it["title"])
            it.pop("published_raw", None)
            salida.append(it)
        salida.sort(key=lambda x: x["published"] or "", reverse=True)
        return salida[:n]

    por_ticker = {}
    for t in tickers:
        por_ticker[t] = prepara(noticias_ticker(t), POR_TICKER)
        print(f"  {t:<6} {len(por_ticker[t])} novedades")
        time.sleep(0.4)

    mercado = prepara(noticias_mercado(), MAX_MERCADO)
    print(f"  mercado: {len(mercado)} titulares")
    calendario = calendario_resultados(tickers)
    print(f"  calendario: {len(calendario)} fechas")

    total = sum(len(v) for v in por_ticker.values()) + len(mercado)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total": total,
        "por_ticker": por_ticker,
        "mercado": mercado,
        "calendario": calendario,
        "fuentes_estado": ESTADO,
        "aviso": ("Las etiquetas (hecho, rumor, analista, resultados, producto) se asignan "
                  "con reglas sobre el titular, no leyendo la noticia. Son una ayuda para "
                  "ordenar, no una verificacion."),
        "errores": ERRORES[:25],
    }

    # No pisar un news.json bueno con uno vacio.
    if total == 0 and OUT.exists():
        try:
            prev = json.loads(OUT.read_text(encoding="utf-8"))
            if prev.get("total"):
                print("Sin noticias nuevas; se conserva el news.json anterior.", file=sys.stderr)
                for e in ERRORES[:25]:
                    print("  !", e)
                return 1
        except Exception:
            pass

    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nnews.json escrito: {total} titulares")
    for k, v in ESTADO.items():
        if v != "ok":
            print(f"  ! {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
