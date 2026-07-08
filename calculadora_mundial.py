"""
⚽ Calculadora de escenarios — Mundial 2026
Convertido de Jupyter Notebook (v2) a Streamlit
"""

import streamlit as st
from itertools import product, combinations
import pandas as pd
import numpy as np
import re
import requests

# ─── CONFIG ─────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="⚽ Calculadora Mundial 2026",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.main-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    padding: 2rem 2rem 1.5rem;
    border-radius: 12px;
    margin-bottom: 1.5rem;
    border-left: 4px solid #e94560;
}
.main-header h1 { color: white; font-size: 2rem; font-weight: 700; margin: 0; }
.main-header p  { color: #a0aec0; margin: 0.3rem 0 0; font-size: 0.95rem; }
div[data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# ─── CONSTANTES CONFIGURABLES ────────────────────────────────────────────────────
PRESETS = {
    "Olímpico — mano a mano primero (FIFA, Euro, La Liga, Serie A)": ["h2h_pts","h2h_dg","h2h_gf","dg","gf"],
    "Diferencia de gol primero (Premier, Bundesliga, Champions fase liga)": ["dg","gf"],
    "Solo puntos (sin desempate fino)": [],
}

if "CRITERIOS"          not in st.session_state: st.session_state.CRITERIOS          = ["h2h_pts","h2h_dg","h2h_gf","dg","gf"]
if "DIRECTO"            not in st.session_state: st.session_state.DIRECTO            = 2
if "MEJORES_TERCEROS"   not in st.session_state: st.session_state.MEJORES_TERCEROS   = 8
if "CAMPEON"            not in st.session_state: st.session_state.CAMPEON            = "campeón"
if "ESTADO"             not in st.session_state: st.session_state.ESTADO             = {}
if "texto_torneo_cache" not in st.session_state: st.session_state.texto_torneo_cache = ""
if "ZONAS"              not in st.session_state: st.session_state.ZONAS              = []
if "ZONAS_TXT"          not in st.session_state: st.session_state.ZONAS_TXT          = ""

def _secret(k, default=""):
    try:
        return st.secrets.get(k, default)
    except Exception:
        return default

def DIRECTO():          return st.session_state.DIRECTO
def MEJORES_TERCEROS(): return st.session_state.MEJORES_TERCEROS
def CAMPEON():          return st.session_state.CAMPEON
def CRITERIOS():        return st.session_state.CRITERIOS

# ─── MOTOR ──────────────────────────────────────────────────────────────────────
def fixture_completo(equipos): return list(combinations(equipos, 2))

def _stats(equipos, partidos):
    st_d = {e: {"pts": 0, "gf": 0, "ga": 0, "pj": 0} for e in equipos}
    for l, v, gl, gv in partidos:
        st_d[l]["gf"] += gl; st_d[l]["ga"] += gv; st_d[l]["pj"] += 1
        st_d[v]["gf"] += gv; st_d[v]["ga"] += gl; st_d[v]["pj"] += 1
        if gl > gv: st_d[l]["pts"] += 3
        elif gl < gv: st_d[v]["pts"] += 3
        else: st_d[l]["pts"] += 1; st_d[v]["pts"] += 1
    for e in st_d: st_d[e]["dg"] = st_d[e]["gf"] - st_d[e]["ga"]
    return st_d

def _stats_entre(teams, partidos):
    ts = set(teams)
    st_d = {e: {"pts": 0, "gf": 0, "ga": 0} for e in teams}
    for l, v, gl, gv in partidos:
        if l in ts and v in ts:
            st_d[l]["gf"] += gl; st_d[l]["ga"] += gv
            st_d[v]["gf"] += gv; st_d[v]["ga"] += gl
            if gl > gv: st_d[l]["pts"] += 3
            elif gl < gv: st_d[v]["pts"] += 3
            else: st_d[l]["pts"] += 1; st_d[v]["pts"] += 1
    for e in st_d: st_d[e]["dg"] = st_d[e]["gf"] - st_d[e]["ga"]
    return st_d

def _resolver(teams, partidos, overall, fair_play, ranking):
    criterios = CRITERIOS()
    if len(teams) <= 1: return list(teams)
    h = _stats_entre(teams, partidos) if any(c.startswith("h2h") for c in criterios) else None
    def val(c):
        if c == "h2h_pts": return {e: h[e]["pts"] for e in teams}
        if c == "h2h_dg":  return {e: h[e]["dg"]  for e in teams}
        if c == "h2h_gf":  return {e: h[e]["gf"]  for e in teams}
        if c == "dg":      return {e: overall[e]["dg"] for e in teams}
        if c == "gf":      return {e: overall[e]["gf"] for e in teams}
        if c == "fair_play" and fair_play is not None: return {e: fair_play.get(e, 0) for e in teams}
        if c == "ranking"   and ranking   is not None: return {e: -ranking.get(e, 9999) for e in teams}
        return None
    for c in criterios:
        vals = val(c)
        if vals is None: continue
        if len(set(vals.values())) > 1:
            out = []
            for v in sorted(set(vals.values()), reverse=True):
                out += _resolver([e for e in teams if vals[e] == v], partidos, overall, fair_play, ranking)
            return out
    return sorted(teams)

def _orden(equipos, partidos, fair_play=None, ranking=None):
    overall = _stats(equipos, partidos); porpts = {}
    for e in equipos: porpts.setdefault(overall[e]["pts"], []).append(e)
    orden = []
    for pts in sorted(porpts, reverse=True):
        orden += _resolver(porpts[pts], partidos, overall, fair_play, ranking)
    return orden, overall

def posiciones(equipos, partidos, fair_play=None, ranking=None):
    orden, _ = _orden(equipos, partidos, fair_play, ranking)
    return {e: i for i, e in enumerate(orden, 1)}

def tabla(equipos, partidos, fair_play=None, ranking=None):
    orden, ov = _orden(equipos, partidos, fair_play, ranking)
    return pd.DataFrame([{"Pos": i, "Equipo": e, "PJ": ov[e]["pj"], "PTS": ov[e]["pts"],
                          "GF": ov[e]["gf"], "GC": ov[e]["ga"], "DG": ov[e]["dg"]}
                         for i, e in enumerate(orden, 1)])

def simular(equipos, jugados, pendientes, resultados, fair_play=None, ranking=None):
    part = list(jugados) + [(l, v, gl, gv) for (l, v), (gl, gv) in zip(pendientes, resultados)]
    return tabla(equipos, part, fair_play, ranking)

def texto_resultados(pend, res):
    return " | ".join(f"{l} {gl}-{gv} {v}" for (l, v), (gl, gv) in zip(pend, res))

def elegir_max_goles(n_pend, tope=300000):
    for mg in (5, 4, 3, 2, 1):
        if (mg + 1) ** (2 * n_pend) <= tope: return mg
    return 1

def todos_los_escenarios(equipos, jugados, pendientes, max_goles=None, fair_play=None, ranking=None):
    if max_goles is None: max_goles = elegir_max_goles(len(pendientes))
    posib = list(product(range(max_goles + 1), repeat=2)); filas = []
    for res in product(posib, repeat=len(pendientes)):
        t = simular(equipos, jugados, pendientes, res, fair_play, ranking)
        fila = {"Resultados": texto_resultados(pendientes, res)}
        for i, ((l, v), (gl, gv)) in enumerate(zip(pendientes, res), 1):
            fila[f"P{i}_local"] = l; fila[f"P{i}_vis"] = v; fila[f"P{i}_gl"] = gl; fila[f"P{i}_gv"] = gv
        for _, r in t.iterrows():
            e = r["Equipo"]; fila[f"Pos {e}"] = r["Pos"]; fila[f"PTS {e}"] = r["PTS"]
            fila[f"DG {e}"] = r["DG"]; fila[f"GF {e}"] = r["GF"]
        filas.append(fila)
    return pd.DataFrame(filas)

# ─── ANÁLISIS ───────────────────────────────────────────────────────────────────
def _pd_de(equipo, pend): return [(i, l, v) for i, (l, v) in enumerate(pend, 1) if equipo in (l, v)]

def _res_propio(row, equipo, pend):
    et = []
    for i, l, v in _pd_de(equipo, pend):
        gl, gv = row[f"P{i}_gl"], row[f"P{i}_gv"]
        gf, gc = (gl, gv) if l == equipo else (gv, gl); riv = v if l == equipo else l
        et.append(f"le gana a {riv}" if gf > gc else (f"pierde con {riv}" if gf < gc else f"empata con {riv}"))
    return " y ".join(et)

def _res_otros(row, equipo, pend):
    et = []; mios = {i for i, _, _ in _pd_de(equipo, pend)}
    for i, (l, v) in enumerate(pend, 1):
        if i in mios: continue
        gl, gv = row[f"P{i}_gl"], row[f"P{i}_gv"]
        et.append(f"gana {l}" if gl > gv else (f"gana {v}" if gl < gv else f"empatan {l} y {v}"))
    return " y ".join(et) if et else "(no hay otros partidos)"

def _combo(row, pend):
    parts = []
    for i, (l, v) in enumerate(pend, 1):
        gl, gv = row[f"P{i}_gl"], row[f"P{i}_gv"]
        parts.append(f"gana {l}" if gl > gv else (f"gana {v}" if gl < gv else f"empatan {l} y {v}"))
    return " · ".join(parts)

def _margen_pend(eq, pend, row):
    m = 0; opp = None
    for i, l, v in _pd_de(eq, pend):
        gl, gv = row[f"P{i}_gl"], row[f"P{i}_gv"]
        m += (gl - gv) if l == eq else (gv - gl)
        opp = v if l == eq else l
    return m, opp

def _gol(k): return f"{abs(k)} gol" + ("es" if abs(k) != 1 else "")

def _detalle_gol(g2, equipo, pend):
    """Describe exactamente cuántos goles necesita para superar a un rival en desempate."""
    fila = g2.iloc[0]; Pe = fila[f"PTS {equipo}"]
    teams = [c[4:] for c in g2.columns if c.startswith("PTS ")]
    rivales = [t for t in teams if t != equipo and g2[f"PTS {t}"].iloc[0] == Pe]
    if len(rivales) != 1:
        extra = f" (igualado en {int(Pe)} pts con {', '.join(rivales)})" if rivales else ""
        return f"depende de la diferencia de gol{extra}"
    riv = rivales[0]
    me0, opp = _margen_pend(equipo, pend, fila); mr0, _ = _margen_pend(riv, pend, fila)
    de = int(fila[f"DG {equipo}"]) - me0; dr = int(fila[f"DG {riv}"]) - mr0
    gap = dr - de; K = gap + 1; riv_pend = bool(_pd_de(riv, pend))
    solo_e = len(_pd_de(equipo, pend)) == 1; solo_r = len(_pd_de(riv, pend)) == 1
    if me0 > 0 and solo_e and solo_r:
        if K >= 2:
            return (f"necesita ganarle a {opp} por al menos {_gol(K)} más que {riv}; "
                    f"si gana por {_gol(K-1)} más, igualan en diferencia de gol y se define por los goles a favor")
        if K == 1:
            return (f"necesita ganarle a {opp} por al menos 1 gol más que {riv}; "
                    f"si ganan por la misma diferencia, igualan en DG y se define por los goles a favor")
        return (f"le alcanza con que su diferencia de gol final supere a la de {riv} (parte {_gol(-gap)} arriba); "
                f"si {riv} la empareja, se define por los goles a favor")
    if me0 > 0 and solo_e and not riv_pend and K >= 1:
        cola = (f"con {_gol(K-1)} igualan en DG y define los goles a favor" if K - 1 >= 1
                else "si igualan la DG, define los goles a favor")
        return f"necesita ganar por al menos {_gol(K)} para superar la diferencia de gol de {riv}; {cola}"
    return (f"necesita terminar con mejor diferencia de gol que {riv} "
            f"(hoy {equipo} {de:+d} y {riv} {dr:+d}); si igualan, se define por los goles a favor")

def situacion(equipo, esc, directo=None):
    d = DIRECTO() if directo is None else directo
    pos = esc[f"Pos {equipo}"]
    vivo = 3 if MEJORES_TERCEROS() > 0 else d
    return {"mejor": int(pos.min()), "peor": int(pos.max()), "total": len(esc),
            "n1": int((pos == 1).sum()), "ndir": int((pos <= d).sum()),
            "ntercero": int((pos == 3).sum()), "ntop3": int((pos <= 3).sum()),
            "ya_1": bool((pos == 1).all()), "ya_directo": bool((pos <= d).all()),
            "puede_1": bool((pos == 1).any()), "puede_directo": bool((pos <= d).any()),
            "puede_tercero": bool((pos == 3).any()), "asegura_vivo": bool((pos <= vivo).all()),
            "eliminado": bool((pos > vivo).all()), "vivo": vivo, "directo": d}

def que_necesita_texto(equipo, esc, pend, objetivo="directo", directo=None, n=2):
    d = DIRECTO() if directo is None else directo
    pos = esc[f"Pos {equipo}"]
    T = sum(1 for c in esc.columns if c.startswith("Pos "))
    if objetivo in ("primero", "campeon"):
        ok = (pos == 1); verbo = f"es {CAMPEON()}"
    elif objetivo == "top3":
        ok = (pos <= 3); verbo = "queda 3º o mejor"
    elif objetivo == "tercero":
        ok = (pos == 3); verbo = "queda 3º"
    elif objetivo == "top":
        ok = (pos <= n); verbo = f"entra al top {n}"
    elif objetivo == "exacto":
        ok = (pos == n); verbo = f"queda {n}º"
    elif objetivo == "descenso":
        corte = T - n; ok = (pos <= corte); verbo = "se salva"
    else:
        ok = (pos <= d); verbo = "clasifica"
    df = esc.copy()
    df["_p"] = df.apply(lambda r: _res_propio(r, equipo, pend), axis=1)
    df["_o"] = df.apply(lambda r: _res_otros(r, equipo, pend), axis=1)
    df["_ok"] = ok.values
    lineas = []
    for prop, g in sorted(df.groupby("_p"), key=lambda kv: -kv[1]["_ok"].mean()):
        m, k = len(g), int(g["_ok"].sum())
        cab = "✅ SEGURO" if k == m else ("❌ IMPOSIBLE" if k == 0 else "⚠️ DEPENDE")
        lineas.append(f"**• Si {equipo} {prop}:** {cab}")
        if 0 < k < m:
            for otros, g2 in sorted(g.groupby("_o"), key=lambda kv: -kv[1]["_ok"].mean()):
                n2, k2 = len(g2), int(g2["_ok"].sum())
                if k2 == n2:
                    e = f"→ {verbo} ✅"
                elif k2 == 0:
                    e = f"→ no {verbo} ❌"
                else:
                    detalle = _detalle_gol(g2, equipo, pend)
                    e = f"→ {detalle} ⚠️"
                lineas.append(f"&nbsp;&nbsp;&nbsp;&nbsp;· y {otros}: {e}")
    return "\n\n".join(lineas)

def apartado_terceros_texto(equipo, esc, pend):
    if MEJORES_TERCEROS() <= 0:
        return ""
    pos = esc[f"Pos {equipo}"]; n3 = int((pos == 3).sum())
    lineas = ["**— MEJOR TERCERO —**"]
    if n3 == 0:
        lineas.append(f"{equipo} no termina 3º en ningún escenario.")
        return "\n\n".join(lineas)
    lineas.append(f"⚠️ Quedar 3º **NO** asegura clasificar: entran los **{MEJORES_TERCEROS()} mejores terceros** del torneo, "
                  f"así que depende de lo que pase en los otros grupos.")
    lineas.append(f"{equipo} termina 3º en **{n3}/{len(esc)}** escenarios.")
    lineas.append(que_necesita_texto(equipo, esc, pend, "tercero"))
    return "\n\n".join(lineas)

def _cab_completo(g, d, hay3):
    pmin, pmax = int(g["_pos"].min()), int(g["_pos"].max())
    if pmax <= d:            return "✅ CLASIFICA DIRECTO"
    if pmin <= d:            return "⚠️ DEPENDE (puede entrar directo)"
    if hay3 and pmax <= 3:   return "⚠️ A LO SUMO 3º (depende de otros grupos)"
    if hay3 and pmin <= 3:   return "⚠️ DEPENDE (3º o afuera)"
    return "❌ QUEDA AFUERA"

def _meaning_pos(equipo, g2, pend, d, hay3):
    pmin, pmax = int(g2["_pos"].min()), int(g2["_pos"].max())
    rng = f"{pmin}º" if pmin == pmax else f"{pmin}º-{pmax}º"
    if pmax <= d:
        return f"→ {rng} · clasifica directo ✅"
    if pmin <= d:
        cola = "si no, 3º (depende de otros grupos)" if hay3 else "si no, afuera"
        return f"→ {rng} · directo según diferencia de gol; {cola} ⚠️"
    if hay3 and pmax <= 3:
        return "→ 3º · entra solo si es de los mejores terceros (depende de otros grupos) ⚠️"
    if hay3 and pmin <= 3:
        return "→ 3º o peor · si es 3º depende de otros grupos; si no, afuera ⚠️"
    return f"→ {rng} · afuera ❌"

def que_necesita_completo_texto(equipo, esc, pend):
    """Árbol único: para cada resultado propio muestra el puesto final (directo / 3º que depende / afuera)."""
    d = DIRECTO(); hay3 = MEJORES_TERCEROS() > 0
    df = esc.copy()
    df["_pos"] = esc[f"Pos {equipo}"].values
    df["_p"] = df.apply(lambda r: _res_propio(r, equipo, pend), axis=1)
    df["_o"] = df.apply(lambda r: _res_otros(r, equipo, pend), axis=1)
    lineas = []
    for prop, g in sorted(df.groupby("_p"), key=lambda kv: kv[1]["_pos"].mean()):
        lineas.append(f"**• Si {equipo} {prop}:** {_cab_completo(g, d, hay3)}")
        uniforme = int(g["_pos"].min()) == int(g["_pos"].max())
        grupos_otros = sorted(g.groupby("_o"), key=lambda kv: kv[1]["_pos"].mean())
        if not uniforme:
            if len(grupos_otros) > 1:
                for otros, g2 in grupos_otros:
                    lineas.append(f"&nbsp;&nbsp;&nbsp;&nbsp;· y {otros}: {_meaning_pos(equipo, g2, pend, d, hay3)}")
            else:
                lineas.append(f"&nbsp;&nbsp;&nbsp;&nbsp;{_meaning_pos(equipo, g, pend, d, hay3)}")
    return "\n\n".join(lineas)

def _mask_gana_todos(esc, equipo, pend):
    mask = pd.Series(True, index=esc.index)
    for i, l, v in _pd_de(equipo, pend):
        gl, gv = esc[f"P{i}_gl"], esc[f"P{i}_gv"]
        mask &= (gl > gv) if l == equipo else (gv > gl)
    return mask

def en_sus_manos(equipo, esc, pend):
    """Devuelve (categoría, frase) sobre si el equipo depende de sí mismo."""
    s = situacion(equipo, esc); d = DIRECTO()
    if s["ya_directo"]: return ("ya", "ya está clasificado directo, pase lo que pase")
    if s["eliminado"]: return ("out", "ya no puede clasificar en ningún escenario")
    own = _pd_de(equipo, pend)
    if not own:
        return ("ayuda", "ya jugó todos sus partidos: su suerte depende solo de los otros")
    mask = _mask_gana_todos(esc, equipo, pend)
    pos = esc[f"Pos {equipo}"]
    n = "su partido" if len(own) == 1 else "todos sus partidos"
    peor = int(pos[mask].max())
    if peor <= d:
        return ("manos", f"lo tiene en sus manos: ganando {n} clasifica directo, sin depender de nadie")
    mejor = int(pos[mask].min())
    if MEJORES_TERCEROS() > 0 and mejor <= 3:
        return ("ayuda", f"aun ganando {n} puede no entrar directo; quedaría como posible mejor 3º (depende de otros grupos)")
    return ("ayuda", f"aun ganando {n} necesita que se den otros resultados")

def en_sus_manos_texto(eqs, jug, esc, pend):
    icon = {"manos": "🟢", "ayuda": "🟡", "ya": "✅", "out": "🔴"}
    lineas = ["**¿Quién depende de sí mismo?**"]
    for _, r in tabla(eqs, jug).iterrows():
        e = r["Equipo"]; cat, msg = en_sus_manos(e, esc, pend)
        lineas.append(f"{icon.get(cat, '•')} **{e}** — {msg}")
    return "\n\n".join(lineas)

def si_terminara_hoy_texto(eqs, jug, pend=None):
    d = DIRECTO(); hay3 = MEJORES_TERCEROS() > 0
    lineas = ["**Si la fase terminara hoy (con la tabla actual):**"]
    for _, r in tabla(eqs, jug).iterrows():
        p = int(r["Pos"])
        if p <= d: est = "✅ clasifica directo"
        elif p == 3 and hay3: est = "🔵 3º — pelearía un lugar entre los mejores terceros"
        else: est = "🔴 quedaría afuera"
        lineas.append(f"{p}º **{r['Equipo']}** · {int(r['PTS'])} pts (DG {int(r['DG']):+d}) — {est}")
    if pend:
        lineas.append(f"_Todavía falta(n) {len(pend)} partido(s); esto puede cambiar._")
    return "\n\n".join(lineas)

_ZCOL = {"campeon": "#1b5e20", "libertadores": "#1b5e20", "sudamericana": "#00838f",
         "clasifica": "#1b5e20", "directo": "#1b5e20", "ascenso": "#1b5e20",
         "repechaje": "#f9a825", "reduccion": "#ef6c00", "promocion": "#ef6c00",
         "playoff": "#f9a825", "descenso": "#b71c1c", "desciende": "#b71c1c"}

def _zlow(s):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", str(s)) if unicodedata.category(c) != "Mn").lower()

def _color_zona(nombre):
    k = _zlow(nombre)
    for key, c in _ZCOL.items():
        if key in k:
            return c
    return _C_NEU

def parse_zonas(text):
    z = []
    for ln in str(text).splitlines():
        ln = ln.strip()
        if not ln:
            continue
        parts = ln.split(None, 1)
        if len(parts) < 2:
            continue
        try:
            hasta = int(parts[0])
        except ValueError:
            continue
        nombre = parts[1].strip()
        z.append((hasta, nombre, _color_zona(nombre)))
    z.sort(key=lambda x: x[0])
    return z

def zona_de(pos, zonas):
    for hasta, nombre, color in zonas:
        if pos <= hasta:
            return nombre, color
    return "—", _C_NEU

def tabla_zonas_texto(eqs, jug, zonas):
    return tabla_zonas_texto_df(tabla(eqs, jug), zonas)

def tabla_zonas_texto_df(orden, zonas):
    L = ["**Si terminara hoy (por zonas):**"]; cur = object()
    for _, r in orden.iterrows():
        p = int(r["Pos"]); nombre, _ = zona_de(p, zonas)
        if nombre != cur:
            L.append(f"\n__{nombre}__"); cur = nombre
        L.append(f"{p}º **{r['Equipo']}** · {int(r['PTS'])} pts (DG {int(r['DG']):+d})")
    return "\n\n".join(L)

def spec_zonas(eqs, jug, zonas):
    return spec_zonas_df(tabla(eqs, jug), zonas)

def spec_zonas_df(orden, zonas):
    if not zonas:
        return None
    rows, cells, seen = [], [], []
    for _, r in orden.iterrows():
        p = int(r["Pos"]); nombre, color = zona_de(p, zonas)
        rows.append(f"{p}º {r['Equipo']}")
        cells.append([(f"{int(r['PTS'])}", color), (f"{int(r['DG']):+d}", color), (nombre, color)])
        if nombre not in [s[1] for s in seen]:
            seen.append((color, nombre))
    return {"titulo": "Tabla por zonas (hoy)", "col_headers": ["Pts", "DG", "Zona"],
            "row_headers": rows, "cells": cells, "corner": "", "leyenda": seen,
            "footer": "Coloreado por zona según la posición actual."}

# ─── MODO LIGA POR TABLA (pegás tabla + «faltan N fechas», sin resultados) ──────
def parse_tabla_fixture(text):
    base, pend, gleft = {}, [], None
    for raw in str(text).splitlines():
        ln = raw.strip()
        if not ln:
            continue
        low = _zlow(ln)
        mf = re.search(r"(\d+)\s*(fecha|fechas|jornada|jornadas)", low)
        if mf and any(w in low for w in ("faltan", "restan", "quedan", "fecha")):
            gleft = int(mf.group(1)); continue
        if not re.search(r"\d", ln) and re.search(r"\s+(?:vs?|x|-|–|—)\s+", ln, flags=re.I):
            p = re.split(r"\s+(?:vs?|x|-|–|—)\s+", ln, flags=re.I)
            if len(p) == 2:
                pend.append((p[0].strip(), p[1].strip())); continue
        ln2 = re.sub(r"^\s*\d+[\.\)]?\s+(?=\D)", "", ln)  # saca posición inicial
        if any(sep in ln2 for sep in (",", ";", "\t")):
            f = [x.strip() for x in re.split(r"[;,\t]", ln2) if x.strip()]
            name = f[0]; nums = [x for x in f[1:] if re.match(r"^[+-]?\d+$", x)]
        else:
            mnum = re.search(r"[+-]?\d", ln2)
            if not mnum:
                continue
            name = ln2[:mnum.start()].strip()
            nums = re.findall(r"[+-]?\d+", ln2[mnum.start():])
        if not name or len(nums) < 1:
            continue
        pts = int(nums[0]); pj = int(nums[1]) if len(nums) > 1 else 0
        dg = int(nums[2]) if len(nums) > 2 else 0
        base[name] = {"pts": pts, "pj": pj, "dg": dg, "gf": max(dg, 0), "ga": max(-dg, 0)}
    return base, pend, gleft

def liga_restantes(equipos, pend, gleft):
    if pend:
        r = {e: 0 for e in equipos}
        for l, v in pend:
            if l in r: r[l] += 1
            if v in r: r[v] += 1
        return r
    return {e: (gleft or 0) for e in equipos}

def liga_tabla_df(base):
    rows = sorted(base.items(), key=lambda kv: (-kv[1]["pts"], -kv[1].get("dg", 0), -kv[1].get("gf", 0)))
    return pd.DataFrame([{"Pos": i, "Equipo": e, "PJ": d.get("pj", 0), "PTS": d["pts"], "DG": d.get("dg", 0)}
                         for i, (e, d) in enumerate(rows, 1)])

def liga_maxmin_df(base, rest):
    rows = [{"Equipo": e, "PJ": d.get("pj", 0), "PTS": d["pts"], "Restan": rest.get(e, 0),
             "PTS máx": d["pts"] + 3 * rest.get(e, 0)} for e, d in base.items()]
    return pd.DataFrame(rows).sort_values(["PTS", "PTS máx"], ascending=False).reset_index(drop=True)

def liga_aseg_df(base, rest, n):
    pts = {e: base[e]["pts"] for e in base}; pmax = {e: pts[e] + 3 * rest.get(e, 0) for e in base}
    rows = []
    for e in base:
        arriba = sum(1 for x in base if x != e and pmax[x] > pts[e])
        inalc = sum(1 for x in base if x != e and pts[x] > pmax[e])
        estado = "🟢 asegurado" if arriba < n else ("🔴 sin chances" if inalc >= n else "🟡 depende")
        rows.append({"Equipo": e, "PTS": pts[e], "PTS máx": pmax[e], f"Top {n}": estado})
    return pd.DataFrame(rows).sort_values("PTS", ascending=False).reset_index(drop=True)

def zona_target(zonas, texto):
    """Devuelve (k_puesto, nombre) para «entrar a X» o «no descender»."""
    if not zonas:
        return None
    t = _zlow(texto)
    if any(w in t for w in ("no desc", "no baj", "salv", "permanec", "mantener la categoria", "no se va")):
        rele = [i for i, (h, n, c) in enumerate(zonas) if c == "#b71c1c"]
        if rele:
            idx = rele[0]
            k = zonas[idx - 1][0] if idx > 0 else zonas[idx][0] - 1
            return max(1, k), "no descender"
    for h, n, c in zonas:
        if _zlow(n) and _zlow(n) in t:
            return h, n
    return None

def _liga_in_out(equipo, base, rest, k):
    pts = {e: base[e]["pts"] for e in base}; pmax = {e: pts[e] + 3 * rest.get(e, 0) for e in base}
    arriba = sum(1 for x in base if x != equipo and pmax[x] > pts[equipo])
    inalc = sum(1 for x in base if x != equipo and pts[x] > pmax[equipo])
    if arriba < k: return "in"
    if inalc >= k: return "out"
    return "pelea"

def liga_duelos_texto(base, rest, pend, zonas):
    if not pend:
        return ("Para los cruces entre rivales directos necesito el **fixture** (los partidos que faltan), no solo «faltan N fechas». "
                "Pegalos como «River vs Boca», uno por línea, y te marco los mano a mano por cada zona.")
    if not zonas:
        return "Configurá las zonas en «🎨 Zonas con nombre» (panel) y te detecto los cruces entre rivales directos."
    L = ["**Cruces entre rivales directos** (partidos que faltan entre dos que pelean la misma zona):"]; any_ = False
    for h, nombre, c in zonas:
        pelea = {e for e in base if _liga_in_out(e, base, rest, h) == "pelea"}
        duelos = [(a, b) for (a, b) in pend if a in pelea and b in pelea]
        if duelos:
            any_ = True; L.append(f"\n__{nombre}__")
            for a, b in duelos:
                L.append(f"• {a} vs {b}")
    if not any_:
        return "No encontré cruces directos entre equipos que peleen la misma zona en el fixture cargado."
    L.append("\n_Estos son los partidos donde un rival le saca puntos directos al otro: valen doble en la pelea._")
    return "\n\n".join(L)

def liga_que_necesita_texto(equipo, base, rest, zonas, texto, pend=None):
    pts = {e: base[e]["pts"] for e in base}; pmax = {e: pts[e] + 3 * rest.get(e, 0) for e in base}
    orden = liga_tabla_df(base); pos = int(orden.set_index("Equipo").loc[equipo, "Pos"])
    tgt = zona_target(zonas, texto)
    if not tgt:
        nombres = ", ".join(n for _, n, _ in zonas) if zonas else "—"
        return f"¿Para qué zona? Configurá las zonas en el panel y preguntá, por ej., «qué necesita {equipo} para Libertadores». Zonas activas: {nombres}."
    k, nombre = tgt
    gx = rest.get(equipo, 0); meta = "no descender" if nombre == "no descender" else f"entrar a {nombre}"
    arriba = sum(1 for x in base if x != equipo and pmax[x] > pts[equipo])
    inalc = sum(1 for x in base if x != equipo and pts[x] > pmax[equipo])
    otros = sorted((pmax[x] for x in base if x != equipo), reverse=True)
    L = [f"**¿Qué necesita {equipo} para {meta}?**",
         f"Está {pos}º con **{pts[equipo]} pts** y le quedan {gx} partidos ({3*gx} en juego)."]
    if arriba < k:
        L.append(f"✅ Ya está adentro de **{nombre}** pase lo que pase.")
    elif inalc >= k:
        L.append(f"❌ Ya no puede entrar a **{nombre}** (matemáticamente quedó afuera).")
    else:
        necesita = max(0, (otros[k-1] + 1) - pts[equipo]) if len(otros) >= k else 0
        if necesita == 0:
            L.append(f"✅ Ya está asegurado en **{nombre}**.")
        elif necesita <= 3 * gx:
            gan = -(-necesita // 3)
            L.append(f"Necesita sumar **{necesita} pts** más (de {3*gx} en juego) para asegurarse — le alcanza con ganar {gan} de los {gx}.")
        else:
            L.append(f"No le alcanza por sí solo: necesitaría {necesita} pts y solo hay {3*gx} en juego → "
                     f"tiene que ganar lo suyo **y** que los rivales pinchen.")
    if pend:
        mios = [(a, b) for (a, b) in pend if equipo in (a, b)]
        if mios:
            rivs = [b if a == equipo else a for (a, b) in mios]
            L.append("Le queda(n) por jugar: " + ", ".join(rivs) + ".")
            directos = [r for r in rivs if r in base and _liga_in_out(r, base, rest, k) == "pelea"]
            if directos:
                L.append(f"⚔️ **Mano a mano:** se cruza con {', '.join(directos)}, rival(es) directo(s) por {nombre} — "
                         f"ganarles vale doble (suma y los deja sin sumar).")
    pq = _porque_liga(equipo, base, rest, zonas, texto)
    if pq:
        L.append("🔍 **Por qué:** " + pq)
    if pend:
        L.append("_El «ya está / quedó afuera» es exacto. Los puntos a sumar son un piso seguro (asume que el resto gana todo lo suyo); "
                 "los cruces directos de arriba ajustan eso a favor._")
    else:
        L.append("_Cuenta por puntos asumiendo que los rivales ganan todo lo suyo (piso seguro). Pegá el **fixture** para ver tus cruces directos._")
    return "\n\n".join(L)

def _porque_liga(equipo, base, rest, zonas, texto):
    tgt = zona_target(zonas, texto)
    if not tgt or equipo not in base:
        return None
    k, nombre = tgt
    pts = {e: base[e]["pts"] for e in base}; pmax = {e: pts[e] + 3 * rest.get(e, 0) for e in base}
    arriba = sum(1 for x in base if x != equipo and pmax[x] > pts[equipo])
    inalc = sum(1 for x in base if x != equipo and pts[x] > pmax[equipo])
    g = rest.get(equipo, 0)
    if arriba < k:
        pueden = sorted([x for x in base if x != equipo and pmax[x] > pts[equipo]], key=lambda x: -pmax[x])
        cuales = f"solo {', '.join(pueden)} pueden terminar por encima" if pueden else "nadie puede terminar por encima"
        return (f"aunque {equipo} pierda todo lo que le queda (se queda en {pts[equipo]}), {cuales}; como entran {k}, ya está adentro.")
    if inalc >= k:
        arr = sorted([x for x in base if x != equipo and pts[x] > pmax[equipo]], key=lambda x: -pts[x])
        muestra = ", ".join(arr[:4]) + (f" y {len(arr)-4} más" if len(arr) > 4 else "")
        return (f"su techo es {pmax[equipo]} pts (ganando sus {g}), y ya hay {inalc} por encima de ese techo "
                f"({muestra}): no los puede pasar.")
    otros = sorted(((x, pmax[x]) for x in base if x != equipo), key=lambda kv: -kv[1])
    rt, rm = otros[k-1]
    falta = max(0, rm + 1 - pts[equipo]); mx = pmax[equipo]
    txt = (f"el {k}º que más puede sumar es {rt} (termina como mucho en {rm}); para asegurarte tenés que "
           f"superarlo ({rm+1}) y hoy tenés {pts[equipo]} → te faltan {falta}.")
    if mx <= rm:
        txt += (f" Y aun ganando todo lo tuyo llegás a {mx}, que no le gana a {rt}: por eso no te alcanza solo, "
                f"necesitás que {rt}" + (" y compañía" if k > 1 else "") + " pinche(n).")
    return txt

def _porque_numero_magico(equipo, eqs, jug, pen, n):
    ov = _stats(eqs, jug); rest = _restantes(eqs, pen)
    pts = {e: ov[e]["pts"] for e in eqs}; pmax = {e: pts[e] + 3 * rest[e] for e in eqs}
    arriba = sum(1 for x in eqs if x != equipo and pmax[x] > pts[equipo])
    if arriba < n:
        return f"aunque {equipo} no sume más, solo {arriba} pueden quedar por encima y entran {n}."
    otros = sorted(((x, pmax[x]) for x in eqs if x != equipo), key=lambda kv: -kv[1])
    rt, rm = otros[n-1]
    return (f"el {n}º que más puede llegar es {rt} (tope {rm}); para asegurarte tenés que pasarlo ({rm+1}) "
            f"y hoy tenés {pts[equipo]} → te faltan {max(0, rm+1-pts[equipo])}.")

def _porque_chances(equipo, esc):
    d = DIRECTO(); T = len(esc); pos = esc[f"Pos {equipo}"]; n = int((pos <= d).sum())
    return (f"de los {T} escenarios posibles (todas las formas en que pueden salir los goles de los partidos que faltan), "
            f"en {n} {equipo} queda entre los {d} primeros y en {T-n} no. Es un conteo de escenarios, no una probabilidad.")

def _porque_bisagra(eqs, jug, pen, esc):
    sc = bisagra_scores(eqs, jug, pen, esc)
    if not sc:
        return None
    a, b = sc[0]["match"]
    return (f"según cómo termine {a} vs {b} cambia más que en cualquier otro partido la cantidad de equipos "
            f"que clasifican; por eso es el que más define.")

def relato_equipo_texto(equipo, eqs, jug, esc, pend):
    d = DIRECTO(); hay3 = MEJORES_TERCEROS() > 0
    pos = posiciones(eqs, jug)[equipo]
    row = tabla(eqs, jug).set_index("Equipo").loc[equipo]
    partes = [f"{equipo} marcha {pos}º del grupo con {int(row.PTS)} puntos (diferencia de gol {int(row.DG):+d})."]
    own = _pd_de(equipo, pend)
    if own:
        rivales = [(v if l == equipo else l) for i, l, v in own]
        partes.append(f"Le queda{'n' if len(rivales) > 1 else ''} por jugar contra {', '.join(rivales)}.")
    cat, manos = en_sus_manos(equipo, esc, pend)
    partes.append(manos[0].upper() + manos[1:] + ".")
    pmin, pmax = int(esc[f"Pos {equipo}"].min()), int(esc[f"Pos {equipo}"].max())
    if pmin != pmax:
        partes.append(f"En el mejor de los casos puede terminar {pmin}º y en el peor, {pmax}º.")
    if not situacion(equipo, esc)["ya_1"] and situacion(equipo, esc)["puede_1"] and pmin == 1:
        partes.append("Todavía tiene chances de quedarse con el primer puesto del grupo.")
    if cat not in ("ya", "out") and own:
        df = esc.copy(); df["_pos"] = esc[f"Pos {equipo}"].values
        df["_p"] = df.apply(lambda r: _res_propio(r, equipo, pend), axis=1)
        frases = []
        for prop, g in sorted(df.groupby("_p"), key=lambda kv: kv[1]["_pos"].mean()):
            pmin, pmax = int(g["_pos"].min()), int(g["_pos"].max())
            if pmax <= d:               res = "se mete entre los que clasifican directo, sin depender de nadie"
            elif pmin <= d:             res = "puede entrar directo, aunque depende del otro resultado y de la diferencia de gol"
            elif hay3 and pmax <= 3:    res = "termina tercero y queda a la espera de ser uno de los mejores terceros del torneo"
            elif hay3 and pmin <= 3:    res = "puede salvarse como tercero o quedar afuera, según los otros grupos"
            else:                       res = "queda eliminado"
            frases.append(f"si {prop}, {res}")
        partes.append("De cara al cierre: " + "; ".join(frases) + ".")
    return " ".join(partes)

def relato_grupo_texto(eqs, jug, esc, pend):
    t = tabla(eqs, jug)
    lider = t.iloc[0]
    partes = [f"{lider.Equipo} encabeza el grupo con {int(lider.PTS)} puntos."]
    clasif, elim, vivos = [], [], []
    for e in eqs:
        s = situacion(e, esc)
        (clasif if s["ya_directo"] else elim if s["eliminado"] else vivos).append(e)
    if clasif: partes.append(("Ya tiene el pasaje asegurado " if len(clasif) == 1 else "Ya tienen el pasaje asegurado ") + ", ".join(clasif) + ".")
    if elim:   partes.append(("Quedó sin chances " if len(elim) == 1 else "Quedaron sin chances ") + ", ".join(elim) + ".")
    if vivos:  partes.append(("Sigue con vida " if len(vivos) == 1 else "Siguen con vida ") + ", ".join(vivos) + ".")
    manos = [e for e in eqs if en_sus_manos(e, esc, pend)[0] == "manos"]
    if manos:  partes.append(("Depende de sí mismo " if len(manos) == 1 else "Dependen de sí mismos ") + ", ".join(manos) + ".")
    if pend:   partes.append("Todo se define en: " + ", ".join(f"{l} vs {v}" for l, v in pend) + ".")
    if pend:
        try:
            sc = bisagra_scores(eqs, jug, pend, esc)
            if sc and sc[0]["swing"] > 0:
                partes.append(f"El partido que más define la clasificación es {sc[0]['match'][0]} vs {sc[0]['match'][1]}.")
        except Exception:
            pass
    if len(t) >= 3:
        margen = int(t.iloc[0]["PTS"]) - int(t.iloc[2]["PTS"])
        partes.append(f"Hoy {t.iloc[0].Equipo} le saca {margen} punto{'s' if margen != 1 else ''} al 3º ({t.iloc[2].Equipo}).")
    return " ".join(partes)

def _celda_estado(g2, d, hay3):
    pmin, pmax = int(g2["_pos"].min()), int(g2["_pos"].max())
    rng = f"{pmin}º" if pmin == pmax else f"{pmin}º-{pmax}º"
    if pmax <= d:            return ("#1b5e20", f"{rng} ✓")
    if pmin <= d:            return ("#ef6c00", "DG")
    if hay3 and pmax <= 3:   return ("#f9a825", "3º*")
    if hay3 and pmin <= 3:   return ("#ef6c00", "3º/✗")
    return ("#b71c1c", "✗")

def matriz_necesita_html(equipo, esc, pend):
    s = spec_necesita(equipo, esc, pend)
    return _html_tabla(s) if s else None

_C_DIR, _C_DG, _C_3, _C_OUT, _C_GREY, _C_HEAD, _C_NEU = "#1b5e20", "#ef6c00", "#f9a825", "#b71c1c", "#9e9e9e", "#f4f6ef", "#eef1e8"

def _is_dark(c):
    c = c.lstrip("#")
    if len(c) != 6: return False
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    return (0.299 * r + 0.587 * g + 0.114 * b) < 150

def _verde(pct):
    t = max(0, min(1, pct / 100))
    r = int(255 + (27 - 255) * t); g = int(255 + (94 - 255) * t); b = int(255 + (32 - 255) * t)
    return f"#{r:02x}{g:02x}{b:02x}"

def _html_tabla(spec):
    th = "padding:8px 10px;font:600 13px Barlow,sans-serif;color:#1a1a2e;border:1px solid #e0e0e0;background:#f4f6ef;text-align:center"
    ch, rh, cells = spec["col_headers"], spec["row_headers"], spec["cells"]
    h = [f'<div style="font:700 17px Barlow,sans-serif;color:#1a1a2e;margin:8px 0 4px">{spec["titulo"]}</div>'] if spec.get("titulo") else []
    h.append('<div style="overflow-x:auto"><table style="border-collapse:collapse;margin:6px 0">')
    h.append(f'<tr><th style="{th};text-align:left">{spec.get("corner","")}</th>' + "".join(f'<th style="{th}">{c}</th>' for c in ch) + "</tr>")
    for i, rl in enumerate(rh):
        h.append(f'<tr><th style="{th};text-align:left">{rl}</th>')
        for j in range(len(ch)):
            text, color = cells[i][j]
            tcol = "#fff" if _is_dark(color) else "#1a1a2e"
            h.append(f'<td style="padding:12px 10px;border:1px solid #fff;text-align:center;background:{color};color:{tcol};font:700 15px Barlow,sans-serif">{text}</td>')
        h.append("</tr>")
    h.append("</table></div>")
    if spec.get("leyenda"):
        chip = "color:#fff;padding:1px 7px;border-radius:3px;font:600 12px Barlow,sans-serif"
        h.append('<div style="margin-top:6px;line-height:2">' + " &nbsp; ".join(f'<span style="background:{c};{chip}">{l}</span>' for c, l in spec["leyenda"]) + "</div>")
    if spec.get("footer"):
        h.append(f'<div style="font:italic 12px Barlow,sans-serif;color:#666;margin-top:4px">{spec["footer"]}</div>')
    return "".join(h)

def _png_tabla(spec):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    from io import BytesIO
    import textwrap
    ch, rh, cells = spec["col_headers"], spec["row_headers"], spec["cells"]
    nC, nR = len(ch), len(rh)
    cw, rhw, rht, headh, titleh = 2.6, 2.6, 0.78, 0.74, 0.6
    legh = 0.5 if spec.get("leyenda") else 0.0
    footh = 0.4 if spec.get("footer") else 0.0
    W, H = rhw + cw * nC, titleh + headh + rht * nR + legh + footh
    fig, ax = plt.subplots(figsize=(W, H), dpi=200)
    ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off"); ax.invert_yaxis()
    if spec.get("titulo"):
        ax.text(0.05, titleh * 0.55, spec["titulo"], fontsize=15, fontweight="bold", color="#1a1a2e", va="center")
    y = titleh
    ax.add_patch(Rectangle((0, y), rhw, headh, facecolor=_C_HEAD, edgecolor="#e0e0e0"))
    ax.text(0.12, y + headh / 2, spec.get("corner", ""), fontsize=9, fontweight="bold", color="#1a1a2e", va="center")
    for j, hd in enumerate(ch):
        x = rhw + cw * j
        ax.add_patch(Rectangle((x, y), cw, headh, facecolor=_C_HEAD, edgecolor="#e0e0e0"))
        ax.text(x + cw / 2, y + headh / 2, "\n".join(textwrap.wrap(str(hd), 18)), fontsize=9, fontweight="bold", color="#1a1a2e", ha="center", va="center")
    y += headh
    for i, rl in enumerate(rh):
        ax.add_patch(Rectangle((0, y), rhw, rht, facecolor=_C_HEAD, edgecolor="#e0e0e0"))
        ax.text(0.12, y + rht / 2, "\n".join(textwrap.wrap(str(rl), 22)), fontsize=9, fontweight="bold", color="#1a1a2e", va="center")
        for j in range(nC):
            text, color = cells[i][j]
            x = rhw + cw * j
            ax.add_patch(Rectangle((x, y), cw, rht, facecolor=color, edgecolor="#ffffff", linewidth=2))
            ax.text(x + cw / 2, y + rht / 2, "\n".join(textwrap.wrap(str(text), 17)), fontsize=11.5, fontweight="bold",
                    color="#fff" if _is_dark(color) else "#1a1a2e", ha="center", va="center")
        y += rht
    if spec.get("leyenda"):
        lx = 0.05
        for color, label in spec["leyenda"]:
            ax.add_patch(Rectangle((lx, y + 0.12), 0.34, 0.26, facecolor=color, edgecolor="none"))
            ax.text(lx + 0.44, y + 0.25, label, fontsize=8.5, color="#444", va="center")
            lx += 0.6 + 0.085 * len(label)
        y += legh
    if spec.get("footer"):
        ax.text(0.05, y + 0.2, spec["footer"], fontsize=8, style="italic", color="#666", va="center")
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white", pad_inches=0.18)
    plt.close(fig)
    return buf.getvalue()

def spec_necesita(equipo, esc, pend):
    if len(_pd_de(equipo, pend)) != 1:
        return None
    d = DIRECTO(); hay3 = MEJORES_TERCEROS() > 0
    df = esc.copy(); df["_pos"] = esc[f"Pos {equipo}"].values
    df["_p"] = df.apply(lambda r: _res_propio(r, equipo, pend), axis=1)
    df["_o"] = df.apply(lambda r: _res_otros(r, equipo, pend), axis=1)
    filas = [k for k, _ in sorted(df.groupby("_p"), key=lambda kv: kv[1]["_pos"].mean())]
    cols = [k for k, _ in sorted(df.groupby("_o"), key=lambda kv: kv[1]["_pos"].mean())]
    cells = []
    for fp in filas:
        row = []
        for c in cols:
            g2 = df[(df["_p"] == fp) & (df["_o"] == c)]
            if len(g2) == 0:
                row.append(("—", "#e0e0e0")); continue
            color, label = _celda_estado(g2, d, hay3)
            row.append((label, color))
        cells.append(row)
    leyenda = [(_C_DIR, "clasifica directo"), (_C_DG, "según dif. de gol"), (_C_3, "3º (depende)"), (_C_OUT, "afuera")]
    return {"titulo": f"Qué necesita {equipo}", "col_headers": cols, "row_headers": filas, "cells": cells,
            "corner": f"{equipo} ⬇ / otros ➡", "leyenda": leyenda,
            "footer": f"Filas = resultado de {equipo}; columnas = el otro partido del grupo."}

def spec_puesto(equipo, esc, pend, puesto):
    if len(_pd_de(equipo, pend)) != 1:
        return None
    df = esc.copy(); df["_pos"] = esc[f"Pos {equipo}"].values
    df["_p"] = df.apply(lambda r: _res_propio(r, equipo, pend), axis=1)
    df["_o"] = df.apply(lambda r: _res_otros(r, equipo, pend), axis=1)
    filas = [k for k, _ in sorted(df.groupby("_p"), key=lambda kv: kv[1]["_pos"].mean())]
    cols = [k for k, _ in sorted(df.groupby("_o"), key=lambda kv: kv[1]["_pos"].mean())]
    cells = []
    for fp in filas:
        row = []
        for c in cols:
            g2 = df[(df["_p"] == fp) & (df["_o"] == c)]
            S = set(int(x) for x in g2["_pos"].unique())
            if S == {puesto}:     row.append((f"{puesto}º ✓", _C_DIR))
            elif puesto in S:     row.append(("a veces", _C_DG))
            else:                 row.append(("—", _C_GREY))
        cells.append(row)
    leyenda = [(_C_DIR, f"termina {puesto}º"), (_C_DG, f"puede ({puesto}º o no)"), (_C_GREY, "no")]
    return {"titulo": f"¿Cuándo {equipo} termina {puesto}º?", "col_headers": cols, "row_headers": filas, "cells": cells,
            "corner": f"{equipo} ⬇ / otros ➡", "leyenda": leyenda,
            "footer": f"Verde = {equipo} queda {puesto}º seguro; ámbar = depende; gris = no llega."}

def spec_mapa(eqs, esc):
    T = len(esc); n = len(eqs)
    order = sorted(eqs, key=lambda e: esc[f"Pos {e}"].mean())
    cols = [f"{k}º" for k in range(1, n + 1)]
    cells = []
    for e in order:
        pos = esc[f"Pos {e}"]; row = []
        for k in range(1, n + 1):
            pct = round(100 * (pos == k).sum() / T)
            row.append((f"{pct}%" if pct else "·", _verde(pct)))
        cells.append(row)
    return {"titulo": "Mapa del grupo · dónde termina cada uno", "col_headers": cols, "row_headers": order, "cells": cells,
            "corner": "equipo ⬇ / puesto ➡", "leyenda": None,
            "footer": "% de escenarios en que cae en cada puesto (conteo de marcadores, no probabilidad real)."}

def spec_comparar(e1, e2, eqs, jug, esc, pend):
    t = tabla(eqs, jug).set_index("Equipo"); pos = posiciones(eqs, jug); rest = _restantes(eqs, pend)
    pmax = lambda e: int(t.loc[e].PTS) + 3 * rest[e]
    s1 = round(100 * (esc[f"Pos {e1}"] < esc[f"Pos {e2}"]).sum() / len(esc))
    s2 = round(100 * (esc[f"Pos {e2}"] < esc[f"Pos {e1}"]).sum() / len(esc))
    N = _C_NEU
    rows = [("Posición actual", [(f"{pos[e1]}º", N), (f"{pos[e2]}º", N)]),
            ("Puntos", [(str(int(t.loc[e1].PTS)), N), (str(int(t.loc[e2].PTS)), N)]),
            ("Dif. de gol", [(f"{int(t.loc[e1].DG):+d}", N), (f"{int(t.loc[e2].DG):+d}", N)]),
            ("Máx. posible", [(str(pmax(e1)), N), (str(pmax(e2)), N)]),
            ("Termina arriba", [(f"{s1}%", _C_DIR if s1 >= s2 else _C_OUT), (f"{s2}%", _C_DIR if s2 > s1 else _C_OUT)])]
    return {"titulo": f"{e1} vs {e2}", "col_headers": [e1, e2], "row_headers": [r[0] for r in rows],
            "cells": [r[1] for r in rows], "corner": "", "leyenda": None,
            "footer": "«Termina arriba» = en qué % de escenarios cada uno queda por encima del otro."}

_R32 = {73: ("2A", "2B"), 74: ("1E", "3ABCDF"), 75: ("1F", "2C"), 76: ("1C", "2F"),
        77: ("1I", "3CDFGH"), 78: ("2E", "2I"), 79: ("1A", "3CEFHI"), 80: ("1L", "3EHIJK"),
        81: ("1D", "3BEFIJ"), 82: ("1G", "3AEHIJ"), 83: ("2K", "2L"), 84: ("1H", "2J"),
        85: ("1B", "3EFGIJ"), 86: ("1J", "2H"), 87: ("1K", "3DEIJL"), 88: ("2D", "2G")}

def _slot_team(slot, ordenes):
    pos = int(slot[0]); lab = slot[1]
    arr = ordenes.get(lab)
    return arr[pos - 1] if arr and len(arr) >= pos else f"{pos}º {lab}"

def camino_equipo(team, grupos):
    """grupos: {label:(eqs,jug,pen)}. Devuelve el cruce de 16avos del equipo según salga 1º/2º/3º."""
    G = next((lab for lab, (eqs, _, _) in grupos.items() if team in eqs), None)
    if not G:
        return None
    ordenes = {lab: list(tabla(eqs, jug)["Equipo"]) for lab, (eqs, jug, _) in grupos.items()}
    def opp_of(slot):
        for m, (a, b) in _R32.items():
            if a == slot: return m, b
            if b == slot: return m, a
        return None, None
    m1, opp1 = opp_of("1" + G)
    m2, opp2 = opp_of("2" + G)
    terceros = []
    for m, (a, b) in _R32.items():
        for slot, other in ((a, b), (b, a)):
            if slot.startswith("3") and G in slot[1:] and other.startswith("1"):
                terceros.append((m, other))
    return {"grupo": G, "ordenes": ordenes, "1": (m1, opp1), "2": (m2, opp2), "3": terceros}

def spec_camino(team, grupos):
    info = camino_equipo(team, grupos)
    if not info:
        return None
    o = info["ordenes"]; G = info["grupo"]
    rows, cells = [], []
    m1, opp1 = info["1"]; m2, opp2 = info["2"]
    rows.append(f"Sale 1º (M{m1})")
    cells.append([(f"{opp1[0]}º del Grupo {opp1[1]}", _C_NEU), (_slot_team(opp1, o), "#1b5e20")])
    rows.append(f"Sale 2º (M{m2})")
    cells.append([(f"{opp2[0]}º del Grupo {opp2[1]}", _C_NEU), (_slot_team(opp2, o), "#2e7d32")])
    if info["3"]:
        wslots = sorted({w for _, w in info["3"]})
        setg = "/".join(s[1] for s in wslots)
        rows.append("Sale 3º (si clasifica)")
        cells.append([(f"1º de {setg}", _C_NEU), (f"uno de {len(wslots)} (ver detalle)", _C_3)])
    return {"titulo": f"Camino de {team} en 16avos · Grupo {G}",
            "col_headers": ["El cruce", "Rival hoy"], "row_headers": rows, "cells": cells,
            "corner": "", "leyenda": None,
            "footer": "Proyección con las posiciones de hoy; el rival cambia según cómo terminen los grupos."}

def camino_texto(team, grupos):
    info = camino_equipo(team, grupos)
    if not info:
        return None
    o = info["ordenes"]; G = info["grupo"]
    st_ = lambda s: _slot_team(s, o)
    m1, opp1 = info["1"]; m2, opp2 = info["2"]
    L = [f"**Camino de {team} en 16avos (Grupo {G}):**",
         f"- Si sale **1º** (Match {m1}): vs **{opp1[0]}º del Grupo {opp1[1]}** → hoy *{st_(opp1)}*.",
         f"- Si sale **2º** (Match {m2}): vs **{opp2[0]}º del Grupo {opp2[1]}** → hoy *{st_(opp2)}*."]
    if info["3"]:
        wslots = sorted({w for _, w in info["3"]})
        cand = ", ".join(f"{st_(s)} (1º {s[1]})" for s in wslots)
        L.append(f"- Si sale **3º** y entra entre los 8 mejores terceros: vs el **ganador** de uno de los grupos "
                 f"{'/'.join(s[1] for s in wslots)} → candidatos hoy: {cand}. "
                 f"(El cruce exacto lo fija la tabla de 495 combinaciones de FIFA cuando terminen los grupos.)")
    L.append("_Proyección con las posiciones actuales; puede cambiar según cómo terminen los grupos._")
    return "\n\n".join(L)

def bisagra_scores(eqs, jug, pen, esc):
    d = DIRECTO(); pos = {e: esc[f"Pos {e}"] for e in eqs}
    res = []
    for i, (L, V) in enumerate(pen, 1):
        gl, gv = esc[f"P{i}_gl"], esc[f"P{i}_gv"]
        masks = {"gana " + L: gl > gv, "empate": gl == gv, "gana " + V: gl < gv}
        swing = 0.0; afectados = []
        for t in eqs:
            ps = []
            for m in masks.values():
                sub = pos[t][m]
                ps.append(100 * (sub <= d).mean() if len(sub) else 0)
            rng = max(ps) - min(ps); swing += rng
            if rng >= 60:
                afectados.append(t)
        res.append({"match": (L, V), "i": i, "swing": swing, "teams": afectados})
    res.sort(key=lambda x: -x["swing"])
    return res

def partido_bisagra_texto(eqs, jug, pen, esc):
    sc = bisagra_scores(eqs, jug, pen, esc)
    if not sc:
        return "No quedan partidos por jugar en el grupo."
    L = ["**Partidos que más definen** (de mayor a menor peso):"]
    for k, s in enumerate(sc):
        a, b = s["match"]; tag = "🔑 " if k == 0 else "• "
        det = (" — decisivo para " + ", ".join(s["teams"])) if s["teams"] else ""
        L.append(f"{tag}**{a} vs {b}**{det}")
    return "\n\n".join(L)

def placa_bisagra_png(eqs, jug, pen, esc):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from io import BytesIO
    sc = bisagra_scores(eqs, jug, pen, esc)
    if not sc:
        return None
    labels = [f"{s['match'][0]} vs {s['match'][1]}" for s in sc]
    vals = [s["swing"] for s in sc]
    cols = ["#1b5e20"] + ["#7aa53d"] * (len(sc) - 1)
    fig, ax = plt.subplots(figsize=(6.8, 0.7 * len(sc) + 1.3), dpi=200)
    ax.barh(range(len(sc)), vals, color=cols, edgecolor="white")
    ax.set_yticks(range(len(sc))); ax.set_yticklabels(labels, fontsize=11.5, fontweight="bold")
    ax.invert_yaxis()
    ax.set_title("Partidos que más definen el grupo", fontsize=14, fontweight="bold", color="#1a1a2e", loc="left")
    for sp in ["top", "right", "bottom"]:
        ax.spines[sp].set_visible(False)
    ax.get_xaxis().set_visible(False)
    if vals:
        ax.text(vals[0] * 0.5, 0, "★ BISAGRA", va="center", ha="center", fontsize=11, color="white", fontweight="bold")
    fig.text(0.01, -0.02, "Mayor barra = el resultado cambia más quién clasifica.", fontsize=8, style="italic", color="#666")
    buf = BytesIO(); fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white", pad_inches=0.2); plt.close(fig)
    return buf.getvalue()

def barras_puesto_png(equipo, esc):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from io import BytesIO
    d = DIRECTO(); hay3 = MEJORES_TERCEROS() > 0
    teams = [c[4:] for c in esc.columns if c.startswith("Pos ")]
    n = len(teams); T = len(esc); pos = esc[f"Pos {equipo}"]
    pcts = [100 * (pos == k).sum() / T for k in range(1, n + 1)]
    cols = ["#1b5e20" if k <= d else ("#f9a825" if (k == 3 and hay3) else "#b71c1c") for k in range(1, n + 1)]
    fig, ax = plt.subplots(figsize=(6.4, 3.5), dpi=200)
    bars = ax.bar([f"{k}º" for k in range(1, n + 1)], pcts, color=cols, edgecolor="white")
    for b, p in zip(bars, pcts):
        ax.text(b.get_x() + b.get_width() / 2, p + 1, f"{p:.0f}%", ha="center", va="bottom", fontsize=11.5, fontweight="bold", color="#1a1a2e")
    ax.set_ylim(0, max(pcts) * 1.2 + 4)
    ax.set_title(f"Dónde puede terminar {equipo}", fontsize=14, fontweight="bold", color="#1a1a2e", loc="left")
    for sp in ["top", "right", "left"]:
        ax.spines[sp].set_visible(False)
    ax.get_yaxis().set_visible(False); ax.tick_params(axis="x", labelsize=12)
    fig.text(0.01, -0.03, "% de escenarios (conteo de marcadores, no probabilidad real). Verde = clasifica.", fontsize=8, style="italic", color="#666")
    buf = BytesIO(); fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white", pad_inches=0.2); plt.close(fig)
    return buf.getvalue()

def _chances_label(pct, s):
    if s.get("ya_directo"): return "YA CLASIFICÓ", "#1b5e20"
    if s.get("eliminado"): return "ELIMINADO", "#b71c1c"
    if pct >= 85: return "MUY BIEN", "#1b5e20"
    if pct >= 60: return "BIEN ENCAMINADO", "#7aa53d"
    if pct >= 40: return "MANO A MANO", "#f9a825"
    if pct >= 15: return "COMPLICADO", "#ef6c00"
    return "CASI SIN CHANCES", "#b71c1c"

def chances_texto(equipo, eqs, jug, esc, pend):
    d = DIRECTO(); hay3 = MEJORES_TERCEROS() > 0; s = situacion(equipo, esc)
    pos = esc[f"Pos {equipo}"]; pct = 100 * float((pos <= d).mean())
    if s["ya_directo"]: pct = 100
    if s["eliminado"]: pct = 0
    verdict, _ = _chances_label(pct, s)
    icon = "✅" if s["ya_directo"] else ("🔴" if s["eliminado"] else ("🟢" if pct >= 60 else ("🟡" if pct >= 40 else "🟠")))
    diez = max(0, min(10, round(pct / 10)))
    L = [f"**¿Cómo viene {equipo}?**", f"{icon} **{verdict}**"]
    if s["ya_directo"]:
        L.append(f"{equipo} ya tiene la clasificación asegurada pase lo que pase.")
    elif s["eliminado"]:
        L.append(f"{equipo} ya no puede clasificar: quedó sin chances matemáticas.")
    else:
        L.append(f"En **{diez} de cada 10** formas en que pueden salir los partidos que faltan, {equipo} clasifica entre los {d} primeros.")
        df = esc.copy(); df["_p"] = df.apply(lambda r: _res_propio(r, equipo, pend), axis=1); df["_ok"] = (pos <= d).values
        rates = {p: g["_ok"].mean() for p, g in df.groupby("_p") if p}
        gana = [p for p in rates if p.startswith("le gana")]
        if gana and all(rates[p] >= 0.999 for p in gana):
            L.append("Lo tiene en sus manos: **ganando** lo suyo queda adentro sin depender de nadie.")
        else:
            cat, manos = en_sus_manos(equipo, esc, pend)
            L.append(manos[0].upper() + manos[1:] + ".")
        if hay3 and s.get("puede_tercero"):
            L.append(f"_Aun sin entrar entre los {d} primeros, puede colarse como uno de los mejores terceros._")
    L.append("_Guía didáctica: cuenta de cuántas formas pueden salir los goles, no es una probabilidad real._")
    return "\n\n".join(L)

def placa_chances_png(equipo, eqs, jug, esc, pend):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.colors import LinearSegmentedColormap
    from io import BytesIO
    d = DIRECTO(); s = situacion(equipo, esc); pos = esc[f"Pos {equipo}"]
    pct = 100 * float((pos <= d).mean())
    if s["ya_directo"]: pct = 100
    if s["eliminado"]: pct = 0
    verdict, _ = _chances_label(pct, s)
    diez = max(0, min(10, round(pct / 10)))
    fig, ax = plt.subplots(figsize=(7.2, 2.2), dpi=200)
    cmap = LinearSegmentedColormap.from_list("c", ["#b71c1c", "#ef6c00", "#f9a825", "#7aa53d", "#1b5e20"])
    ax.imshow(np.linspace(0, 1, 256).reshape(1, -1), extent=[0, 100, 0, 1], aspect="auto", cmap=cmap)
    ax.plot([pct], [1.12], marker="v", markersize=18, color="#1a1a2e", clip_on=False)
    ax.text(pct, 1.45, verdict, ha="center", va="bottom", fontsize=15, fontweight="bold", color="#1a1a2e", clip_on=False)
    for x, lab in [(10, "Casi nada"), (30, "Difícil"), (50, "Parejo"), (70, "Probable"), (90, "Casi seguro")]:
        ax.text(x, -0.22, lab, ha="center", va="top", fontsize=9.5, color="#444")
    ax.set_xlim(0, 100); ax.set_ylim(-1.4, 2.3); ax.axis("off")
    ax.set_title(f"¿Cómo viene {equipo}?", fontsize=15, fontweight="bold", color="#1a1a2e", loc="left", y=0.92)
    sub = ("Ya clasificó" if s["ya_directo"] else ("Quedó eliminado" if s["eliminado"]
           else f"Clasifica en {diez} de cada 10 formas posibles"))
    ax.text(50, -0.62, sub, ha="center", va="top", fontsize=10.5, style="italic", color="#555")
    buf = BytesIO(); fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white", pad_inches=0.3); plt.close(fig)
    return buf.getvalue()

def aplicar_resultados(eqs, jugados, pend, fixed):
    """fixed: {indice_1based: 'L'/'E'/'V'}. Triunfos 1-0, empates 0-0. Devuelve (jugados_sim, pendientes_restantes)."""
    jug = list(jugados); rem = []
    for i, (l, v) in enumerate(pend, 1):
        o = fixed.get(i)
        if o == "L":   jug.append((l, v, 1, 0))
        elif o == "E": jug.append((l, v, 0, 0))
        elif o == "V": jug.append((l, v, 0, 1))
        else:          rem.append((l, v))
    return jug, rem

def filtrar_esc(esc, fixed):
    m = pd.Series(True, index=esc.index)
    for i, o in fixed.items():
        gl, gv = esc[f"P{i}_gl"], esc[f"P{i}_gv"]
        if o == "L":   m &= gl > gv
        elif o == "E": m &= gl == gv
        elif o == "V": m &= gl < gv
    return esc[m]

def previa_condicional_texto(eqs, jugados, pend, esc, fixed):
    d = DIRECTO(); hay3 = MEJORES_TERCEROS() > 0
    desc = []
    for i, (l, v) in enumerate(pend, 1):
        o = fixed.get(i)
        if o == "L":   desc.append(f"{l} le gana a {v}")
        elif o == "E": desc.append(f"empatan {l} y {v}")
        elif o == "V": desc.append(f"{v} le gana a {l}")
    sub = filtrar_esc(esc, fixed)
    if len(sub) == 0:
        return "Esa combinación no es posible con los partidos cargados."
    L = []
    if desc:
        L.append("**Si " + ", y ".join(desc) + ":**")
    clasi, afue, dep = [], [], []
    for e in eqs:
        pos = sub[f"Pos {e}"]; r = float((pos <= d).mean())
        if r >= 0.999:
            clasi.append(e)
        elif r <= 0.001:
            if hay3 and float((pos == 3).mean()) > 0:
                dep.append(e + " (a pelear el 3er puesto)")
            else:
                afue.append(e)
        else:
            dep.append(e)
    if clasi: L.append(f"Clasifican entre los {d}: **{', '.join(clasi)}**.")
    if dep:   L.append("En duda según el resto: " + ", ".join(dep) + ".")
    if afue:  L.append("Quedaría(n) afuera: " + ", ".join(afue) + ".")
    rem = [f"{l} vs {v}" for i, (l, v) in enumerate(pend, 1) if i not in fixed]
    if rem:
        L.append("_Falta definir: " + ", ".join(rem) + "._")
    L.append("_La tabla de arriba asume triunfos 1-0 y empates 0-0 (el DG real depende del marcador). La clasificación considera todos los marcadores posibles de los partidos que fijaste; en empates de puntos muy finos puede definirse por desempate._")
    return "\n\n".join(L)

def _branch_label(equipo, own, combo):
    parts = []
    for i, l, v in own:
        o = combo[i]; other = v if l == equipo else l
        if (o == "L" and l == equipo) or (o == "V" and v == equipo):
            parts.append(f"le gana a {other}")
        elif o == "E":
            parts.append(f"empata con {other}")
        else:
            parts.append(f"pierde con {other}")
    return " y ".join(parts)

def arbol_branches(equipo, eqs, jug, esc, pend):
    import itertools
    own = _pd_de(equipo, pend)
    if not own or len(own) > 2:
        return None
    d = DIRECTO(); hay3 = MEJORES_TERCEROS() > 0
    res = []
    for vals in itertools.product(["L", "E", "V"], repeat=len(own)):
        combo = {i: o for (i, l, v), o in zip(own, vals)}
        m = pd.Series(True, index=esc.index)
        for i, o in combo.items():
            gl, gv = esc[f"P{i}_gl"], esc[f"P{i}_gv"]
            m &= (gl > gv) if o == "L" else ((gl == gv) if o == "E" else (gl < gv))
        sub = esc[m]
        if len(sub) == 0:
            continue
        pos = sub[f"Pos {equipo}"]; rd = float((pos <= d).mean()); r3 = float((pos == 3).mean())
        if rd >= 0.999:
            verd, col = "Clasifica", "#1b5e20"
        elif rd <= 0.001:
            verd, col = ("Pelea 3º", "#f9a825") if (hay3 and r3 > 0) else ("Afuera", "#b71c1c")
        else:
            verd, col = "Depende", "#ef6c00"
        # orden desde la óptica del equipo: gana(0) / empata(1) / pierde(2)
        pkey = []
        for i, l, v in own:
            o = combo[i]
            pkey.append(0 if ((o == "L" and l == equipo) or (o == "V" and v == equipo)) else (1 if o == "E" else 2))
        res.append({"label": _branch_label(equipo, own, combo).capitalize(), "verd": verd,
                    "col": col, "key": tuple(pkey)})
    res.sort(key=lambda r: r["key"])
    return res

def placa_arbol_png(equipo, eqs, jug, esc, pend):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
    import textwrap
    from io import BytesIO
    br = arbol_branches(equipo, eqs, jug, esc, pend)
    if not br:
        return None
    n = len(br); fig, ax = plt.subplots(figsize=(7.6, 0.92 * n + 1.1), dpi=200)
    ax.set_xlim(0, 10); ax.set_ylim(0, n); ax.axis("off")
    ax.set_title(f"¿Qué pasa con {equipo}?", fontsize=15, fontweight="bold", color="#1a1a2e", loc="left", pad=12)
    ymid = n / 2
    ax.add_patch(FancyBboxPatch((0.1, ymid - 0.42), 2.3, 0.84, boxstyle="round,pad=0.03,rounding_size=0.12",
                                facecolor="#1a1a2e", edgecolor="none"))
    ax.text(1.25, ymid, equipo, ha="center", va="center", color="white", fontsize=12, fontweight="bold")
    for j, b in enumerate(br):
        y = n - 0.5 - j
        ax.plot([2.4, 3.4], [ymid, y], color="#bbb", lw=2, zorder=0)
        ax.add_patch(FancyBboxPatch((3.4, y - 0.36), 3.6, 0.72, boxstyle="round,pad=0.03,rounding_size=0.1",
                                    facecolor="#eef1e8", edgecolor="#d8ddcf"))
        ax.text(5.2, y, "\n".join(textwrap.wrap(b["label"], 26)), ha="center", va="center", fontsize=10.5,
                color="#1a1a2e", fontweight="bold")
        ax.plot([7.0, 7.5], [y, y], color="#bbb", lw=2, zorder=0)
        ax.add_patch(FancyBboxPatch((7.5, y - 0.36), 2.3, 0.72, boxstyle="round,pad=0.03,rounding_size=0.1",
                                    facecolor=b["col"], edgecolor="none"))
        ax.text(8.65, y, b["verd"], ha="center", va="center", color="white", fontsize=11, fontweight="bold")
    fig.text(0.01, -0.02, "Según el resultado de su partido. «Depende» = puede clasificar o no según los otros partidos.",
             fontsize=8, style="italic", color="#666")
    buf = BytesIO(); fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white", pad_inches=0.25); plt.close(fig)
    return buf.getvalue()

def _porque_pasar(equipo, eqs, jug, esc, pend, n):
    d = DIRECTO(); hay3 = MEJORES_TERCEROS() > 0
    s = situacion(equipo, esc, d)
    ov = _stats(eqs, jug); rest = _restantes(eqs, pend)
    pts = {e: ov[e]["pts"] for e in eqs}; pmax = {e: pts[e] + 3 * rest[e] for e in eqs}
    p = pts[equipo]; mx = pmax[equipo]; g = rest[equipo]
    def lst(ts, lim=4):
        ts = list(ts); return ", ".join(ts[:lim]) + (f" y {len(ts)-lim} más" if len(ts) > lim else "")
    # YA CLASIFICADO ENTRE LOS DIRECTOS
    if s["ya_directo"]:
        nopas = sorted([x for x in eqs if x != equipo and pmax[x] < p], key=lambda x: -pmax[x])
        extra = ("; " + "; ".join(f"{x}, aun ganando todo, llega a {pmax[x]}" for x in nopas[:3]) + " — no te alcanzan") if nopas else ""
        return f"{equipo} ya termina entre los {d} pase lo que pase: tiene {p} pts y los de atrás no lo pueden dejar afuera{extra}."
    # ELIMINADO DE TODO (ni mejor tercero)
    if s["eliminado"]:
        arr = sorted([x for x in eqs if x != equipo and pts[x] > mx], key=lambda x: -pts[x])
        det = f" Ya hay {len(arr)} por encima de su techo de {mx} ({lst(arr)}), no los puede pasar." if arr else ""
        cola = " (ni siquiera le da para pelear el mejor tercero)" if hay3 else ""
        return f"{equipo} quedó afuera{cola}: su techo es {mx} pts (ganando sus {g}) y no alcanza.{det}"
    # EN JUEGO
    pueden = sorted([x for x in eqs if x != equipo and pmax[x] >= p], key=lambda x: -pmax[x])
    partes = []
    if s["puede_directo"]:
        if pueden:
            partes.append(f"{equipo} tiene {p} pts (techo {mx}) y puede entrar entre los {d}, pero todavía lo pueden alcanzar {lst(pueden)}, así que depende de esos partidos")
        else:
            partes.append(f"{equipo} puede entrar entre los {d}")
        igualan = [x for x in eqs if x != equipo and pmax[x] >= mx]
        if len(igualan) >= n:
            partes.append(f"aun ganando todo (llega a {mx}) no se asegura, porque {lst(igualan)} también pueden llegar a {mx} o más")
        if hay3 and s["puede_tercero"]:
            partes.append(f"si no entra entre los {d}, igual puede colarse como **mejor tercero**, que depende de cómo terminen los otros grupos")
    else:
        if hay3 and s["asegura_vivo"]:
            partes.append(f"{equipo} ya no entra entre los {d}, pero tiene **asegurado el 3er puesto**; que ese 3º clasifique depende de los otros grupos (entran los 8 mejores terceros)")
        elif hay3 and s["puede_tercero"]:
            partes.append(f"{equipo} ya no entra entre los {d}; su chance es ser uno de los **mejores terceros**, que depende de cómo terminen los otros grupos")
        else:
            partes.append(f"{equipo} la tiene muy cuesta arriba")
    return ". ".join(x[0].upper() + x[1:] for x in partes) + "."

# ═══ CIENCIA DE DATOS: fuerza estimada, Monte Carlo liga, proyección, importador ═══

# ── Métricas periodísticas: forma, rachas, local/visitante, dificultad de fixture ──

def _res_letra(e, l, v, gl, gv):
    if gl == gv: return "E"
    return "G" if (l if gl > gv else v) == e else "P"

def forma_equipo(e, jug, n=5):
    letras = [_res_letra(e, l, v, gl, gv) for (l, v, gl, gv) in jug if e in (l, v)]
    ult = letras[-n:]
    pts = sum(3 if x == "G" else (1 if x == "E" else 0) for x in ult)
    return ult, pts

def racha_equipo(e, jug):
    letras = [_res_letra(e, l, v, gl, gv) for (l, v, gl, gv) in jug if e in (l, v)]
    if not letras:
        return "sin partidos"
    last = letras[-1]; k = 0
    for x in reversed(letras):
        if x == last: k += 1
        else: break
    inv = 0
    for x in reversed(letras):
        if x in ("G", "E"): inv += 1
        else: break
    sinv = 0
    for x in reversed(letras):
        if x in ("P", "E"): sinv += 1
        else: break
    if last == "G":
        return f"{k} victoria{'s' if k>1 else ''} al hilo" + (f" ({inv} invicto)" if inv > k else "")
    if last == "E":
        if inv > k: return f"{inv} partidos invicto"
        if sinv > k: return f"{sinv} sin ganar"
        return f"{k} empate{'s' if k>1 else ''} seguido{'s' if k>1 else ''}"
    return f"{k} derrota{'s' if k>1 else ''} al hilo" + (f" ({sinv} sin ganar)" if sinv > k else "")

def tabla_forma_df(eqs, jug, n=5):
    ov = _stats(eqs, jug)
    rows = []
    for e in eqs:
        ult, p5 = forma_equipo(e, jug, n)
        rows.append({"Equipo": e, "PTS": ov[e]["pts"], "Últimos 5": "".join(ult) or "—",
                     "Pts últ. 5": p5, "Racha": racha_equipo(e, jug)})
    return pd.DataFrame(rows).sort_values(["Pts últ. 5", "PTS"], ascending=False).reset_index(drop=True)

def local_visitante_df(eqs, jug):
    rows = []
    for e in eqs:
        pl = pjl = pv = pjv = 0
        for (l, v, gl, gv) in jug:
            if l == e:
                pjl += 1; pl += 3 if gl > gv else (1 if gl == gv else 0)
            elif v == e:
                pjv += 1; pv += 3 if gv > gl else (1 if gl == gv else 0)
        rows.append({"Equipo": e, "PJ local": pjl, "Pts local": pl,
                     "Pts/PJ local": round(pl / pjl, 2) if pjl else 0.0,
                     "PJ visita": pjv, "Pts visita": pv,
                     "Pts/PJ visita": round(pv / pjv, 2) if pjv else 0.0})
    return pd.DataFrame(rows).sort_values("Pts/PJ local", ascending=False).reset_index(drop=True)

def dificultad_fixture_df(eqs, pen, ppg, rest=None):
    med = (sum(ppg.values()) / len(ppg)) if ppg else 0.0
    rows = []
    for e in eqs:
        rivs = [v if l == e else l for (l, v) in pen if e in (l, v)]
        extra = max(0, (rest or {}).get(e, len(rivs)) - len(rivs)) if rest else 0
        vals = [ppg.get(r, med) for r in rivs] + [med] * extra
        idx = round(sum(vals) / len(vals), 2) if vals else np.nan
        rows.append({"Equipo": e, "Restan": len(rivs) + extra,
                     "Rivales que quedan": (", ".join(rivs[:6]) + ("…" if len(rivs) > 6 else "")) or "—",
                     "Dificultad (pts/PJ rival)": idx})
    return pd.DataFrame(rows).sort_values("Dificultad (pts/PJ rival)", ascending=False,
                                          na_position="last").reset_index(drop=True)

def ficha_equipo_texto(e, eqs, jug, pen):
    ov = _stats(eqs, jug); t = tabla(eqs, jug)
    pos = list(t["Equipo"]).index(e) + 1 if e in list(t["Equipo"]) else "?"
    d = ov[e]; pj = d["pj"]; ppg = d["pts"] / pj if pj else 0.0
    ult, p5 = forma_equipo(e, jug)
    pl = pjl = pv = pjv = 0
    for (l, v, gl, gv) in jug:
        if l == e:   pjl += 1; pl += 3 if gl > gv else (1 if gl == gv else 0)
        elif v == e: pjv += 1; pv += 3 if gv > gl else (1 if gl == gv else 0)
    rest = _restantes(eqs, pen)
    rivs = [v if l == e else l for (l, v) in pen if e in (l, v)]
    ppgs = {x: (ov[x]["pts"] / ov[x]["pj"]) if ov[x]["pj"] else 0.0 for x in eqs}
    med = (sum(ppgs.values()) / len(ppgs)) if ppgs else 0.0
    dif = round(sum(ppgs.get(r, med) for r in rivs) / len(rivs), 2) if rivs else None
    L = [f"**Ficha de {e}**",
         f"{pos}º con **{d['pts']} pts** en {pj} PJ ({round(ppg,2)} por partido) · GF {d['gf']} / GC {d['ga']} (DG {d['dg']:+d}).",
         f"**Forma (últ. 5):** {''.join(ult) or '—'} ({p5} pts) · **Racha:** {racha_equipo(e, jug)}.",
         f"**Local:** {pl} pts en {pjl} PJ ({round(pl/pjl,2) if pjl else 0}/PJ) · **Visitante:** {pv} pts en {pjv} PJ ({round(pv/pjv,2) if pjv else 0}/PJ)."]
    if rivs:
        L.append(f"**Le quedan {rest[e]}:** {', '.join(rivs)}" +
                 (f" · dificultad {dif} pts/PJ ({'más brava que' if dif and dif>med else 'más liviana que'} la media {round(med,2)})." if dif is not None else "."))
    L.append(f"**Techo:** {d['pts'] + 3*rest[e]} pts ganando todo.")
    return "\n\n".join(L)

def ficha_liga_texto(e, base, rest, pend, zonas):
    t = liga_tabla_df(base); pos = int(t.set_index("Equipo").loc[e, "Pos"])
    d = base[e]; pj = d.get("pj", 0); ppg = d["pts"] / pj if pj else 0.0; r = rest.get(e, 0)
    z = zona_de(pos, zonas)[0] if zonas else "—"
    rivs = [v if l == e else l for (l, v) in pend if e in (l, v)]
    ppgs = {x: (base[x]["pts"] / base[x].get("pj", 1)) if base[x].get("pj") else 0.0 for x in base}
    med = (sum(ppgs.values()) / len(ppgs)) if ppgs else 0.0
    L = [f"**Ficha de {e}**",
         f"{pos}º con **{d['pts']} pts** en {pj} PJ ({round(ppg,2)} por partido) · DG {d.get('dg',0):+d} · Zona hoy: **{z}**.",
         f"**Le quedan {r} partidos** ({3*r} pts en juego) · **Proyección a este ritmo:** {round(d['pts'] + ppg*r,1)} pts · **Techo:** {d['pts'] + 3*r}."]
    if rivs:
        dif = round(sum(ppgs.get(x, med) for x in rivs) / len(rivs), 2)
        L.append(f"**Rivales que quedan:** {', '.join(rivs)} · dificultad {dif} pts/PJ (media {round(med,2)}).")
    else:
        L.append("_Pegá el fixture («A vs B») para ver rivales y dificultad del calendario. Para forma y local/visitante, importá los resultados (JSON del actor) o pegalos._")
    return "\n\n".join(L)

def fuerza_desde_stats(eqs, jug):
    """Fuerza por equipo: mezcla rendimiento global (70%) + forma últimos 5 (30%)."""
    ov = _stats(eqs, jug)
    ppg = {e: (ov[e]["pts"] / ov[e]["pj"]) if ov[e]["pj"] else 1.0 for e in eqs}
    ppg5 = {}
    for e in eqs:
        ult, p5 = forma_equipo(e, jug, 5)
        ppg5[e] = (p5 / len(ult)) if ult else ppg[e]
    mix = {e: 0.7 * ppg[e] + 0.3 * ppg5[e] for e in eqs}
    med = sum(mix.values()) / len(mix) if mix else 1.0
    if not med:
        return None
    return {e: min(1.7, max(0.55, mix[e] / med)) for e in eqs}

def _fuerza_liga(base):
    ppg = {e: (d["pts"] / d.get("pj", 0)) if d.get("pj") else 1.0 for e, d in base.items()}
    med = sum(ppg.values()) / len(ppg) if ppg else 1.0
    return {e: min(1.8, max(0.4, (ppg[e] / med) if med else 1.0)) for e in base}

def liga_probabilidades_df(base, rest, pend, zonas, n=4000, seed=7, pdraw=0.26):
    """Monte Carlo del cierre de la liga: % de terminar en cada zona. Usa el fixture pegado
    para los cruces reales y rival promedio para los partidos sin rival conocido."""
    rng = np.random.default_rng(seed)
    eqs = list(base.keys()); idx = {e: i for i, e in enumerate(eqs)}
    s = _fuerza_liga(base)
    pts0 = np.array([base[e]["pts"] for e in eqs], float)
    dg0 = np.array([float(base[e].get("dg", 0)) for e in eqs])
    pts = np.tile(pts0, (n, 1))
    fix = [(a, b) for (a, b) in pend if a in idx and b in idx]
    en_fix = {e: 0 for e in eqs}
    for a, b in fix:
        en_fix[a] += 1; en_fix[b] += 1
        pa = (1 - pdraw) * (s[a] * 1.22) / (s[a] * 1.22 + s[b])  # ventaja de localía
        u = rng.random(n)
        ga = u < pa; gb = u >= pa + pdraw
        pts[:, idx[a]] += np.where(ga, 3, np.where(gb, 0, 1))
        pts[:, idx[b]] += np.where(gb, 3, np.where(ga, 0, 1))
    for e in eqs:
        extra = max(0, rest.get(e, 0) - en_fix[e])
        if extra:
            pa = (1 - pdraw) * s[e] / (s[e] + 1.0)
            u = rng.random((n, extra))
            pts[:, idx[e]] += np.where(u < pa, 3, np.where(u < pa + pdraw, 1, 0)).sum(axis=1)
    key = pts + dg0[None, :] * 1e-4 + rng.random((n, len(eqs))) * 1e-7
    pos = np.argsort(np.argsort(-key, axis=1), axis=1) + 1
    bandas = []
    prev = 0
    for h, nombre, _c in sorted(zonas or [], key=lambda z: z[0]):
        bandas.append((prev + 1, h, nombre)); prev = h
    rows = []
    orden = sorted(eqs, key=lambda e: (-base[e]["pts"], -base[e].get("dg", 0)))
    for e in orden:
        p = pos[:, idx[e]]
        row = {"Equipo": e, "PTS": base[e]["pts"], "1º %": round(100 * float((p == 1).mean()), 1)}
        for lo, hi, nombre in bandas:
            row[f"{nombre} %"] = round(100 * float(((p >= lo) & (p <= hi)).mean()), 1)
        if not bandas:
            row["Top 3 %"] = round(100 * float((p <= 3).mean()), 1)
        rows.append(row)
    return pd.DataFrame(rows)

NOTA_MC_LIGA = ("_Estimación por simulación (4.000 torneos): la fuerza de cada equipo sale de sus puntos por "
                "partido (ponderando la forma reciente si hay resultados), con los cruces reales del fixture, "
                "ventaja de localía y rival promedio en lo demás. Es una guía para la nota, no un pronóstico: "
                "no ve lesiones ni bajas._")

def liga_proyeccion_df(base, rest):
    rows = []
    for e, d in base.items():
        pj = d.get("pj", 0); ppg = (d["pts"] / pj) if pj else 0.0; r = rest.get(e, 0)
        rows.append({"Equipo": e, "PJ": pj, "PTS": d["pts"], "Pts/partido": round(ppg, 2), "Restan": r,
                     "Proyección (ritmo)": round(d["pts"] + ppg * r, 1), "Techo": d["pts"] + 3 * r})
    return pd.DataFrame(rows).sort_values(["Proyección (ritmo)", "PTS"], ascending=False).reset_index(drop=True)

def liga_comparar_df(a, b, base, rest, zonas):
    t = liga_tabla_df(base).set_index("Equipo")
    def fila(e):
        pos = int(t.loc[e, "Pos"]); pj = base[e].get("pj", 0); r = rest.get(e, 0)
        z = zona_de(pos, zonas)[0] if zonas else "—"
        return {"Posición": pos, "Puntos": base[e]["pts"], "PJ": pj, "DG": base[e].get("dg", 0),
                "Pts/partido": round(base[e]["pts"] / pj, 2) if pj else 0.0,
                "Restan": r, "Techo": base[e]["pts"] + 3 * r, "Zona hoy": z}
    fa, fb = fila(a), fila(b)
    return pd.DataFrame([{"Dato": k, a: fa[k], b: fb[k]} for k in fa])

def chances_mc(equipo, eqs, jug, pen, n=6000):
    """Chances de clasificar sin enumeración: simulación con fuerza estimada. Devuelve (pct, df)."""
    d = DIRECTO()
    f = fuerza_desde_stats(eqs, jug)
    df = probabilidades(eqs, jug, pen, n=n, fuerza=f)
    col = "1º %" if d == 1 else ("Top 2 %" if d == 2 else "Top 3 %")
    fila = df[df["Equipo"] == equipo]
    pct = float(fila[col].iloc[0]) if len(fila) else 0.0
    return pct, df

def placa_chances_mc_png(equipo, pct, nota="Estimación por simulación"):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
    from io import BytesIO
    verdict, _ = _chances_label(pct, {})
    fig, ax = plt.subplots(figsize=(7.2, 2.2), dpi=200)
    cmap = LinearSegmentedColormap.from_list("c", ["#b71c1c", "#ef6c00", "#f9a825", "#7aa53d", "#1b5e20"])
    ax.imshow(np.linspace(0, 1, 256).reshape(1, -1), extent=[0, 100, 0, 1], aspect="auto", cmap=cmap)
    ax.plot([pct], [1.12], marker="v", markersize=18, color="#1a1a2e", clip_on=False)
    ax.text(pct, 1.45, verdict, ha="center", va="bottom", fontsize=15, fontweight="bold", color="#1a1a2e", clip_on=False)
    for x, lab in [(10, "Casi nada"), (30, "Difícil"), (50, "Parejo"), (70, "Probable"), (90, "Casi seguro")]:
        ax.text(x, -0.22, lab, ha="center", va="top", fontsize=9.5, color="#444")
    ax.set_xlim(0, 100); ax.set_ylim(-1.4, 2.3); ax.axis("off")
    ax.set_title(f"¿Cómo viene {equipo}?", fontsize=15, fontweight="bold", color="#1a1a2e", loc="left", y=0.92)
    ax.text(50, -0.62, nota, ha="center", va="top", fontsize=10.5, style="italic", color="#555")
    buf = BytesIO(); fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white", pad_inches=0.3); plt.close(fig)
    return buf.getvalue()

def partidos_desde_url(url):
    """Lee la tabla cruzada (matriz equipo × equipo) de una página tipo Wikipedia.
    Devuelve (jugados, pendientes, error, nota). Las celdas con marcador son resultados;
    las vacías, partidos por jugar. Detecta si el torneo es ida y vuelta o una sola rueda."""
    import requests as _rq, io as _io
    try:
        html = _rq.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30).text
    except Exception as e:
        return [], [], f"No pude descargar la página: {e}", ""
    try:
        tablas = pd.read_html(_io.StringIO(html))
    except Exception as e:
        return [], [], f"No encontré tablas legibles ({e}).", ""
    rx = re.compile(r"(\d+)\s*[–—:\-]\s*(\d+)")
    jugados, pend = [], []
    doble = False; encontrados = 0
    for t in tablas:
        n = len(t)
        if n < 4 or len(t.columns) != n + 1:
            continue
        nombres, ok = [], True
        for _, row in t.iterrows():
            nm = str(row.iloc[0]).strip()
            nm = re.sub(r"\s*\[[^\]]*\]", "", nm)
            nm = re.sub(r"\s*\([^)]*\)\s*$", "", nm).strip()
            if not nm or nm.lower() == "nan" or rx.search(nm):
                ok = False; break
            nombres.append(nm)
        if not ok or len(set(nombres)) != n:
            continue
        encontrados += 1
        mat = {}
        for i in range(n):
            for j in range(1, n + 1):
                if j - 1 == i:
                    continue
                a, b = nombres[i], nombres[j - 1]
                m = rx.search(str(t.iat[i, j]))
                mat[(a, b)] = (int(m.group(1)), int(m.group(2))) if m else None
        if any(v is not None and mat.get((b, a)) is not None for (a, b), v in mat.items()):
            doble = True
        for (a, b), v in mat.items():
            if v is not None:
                jugados.append((a, b, v[0], v[1]))
        vistos = set()
        for (a, b), v in mat.items():
            if v is None:
                if doble:
                    pend.append((a, b))
                else:
                    key = frozenset((a, b))
                    if key in vistos:
                        continue
                    vistos.add(key)
                    if mat.get((b, a)) is None:
                        pend.append((a, b))
    if not encontrados:
        return [], [], ("No encontré la tabla cruzada (matriz equipo × equipo) en esa página. "
                        "Probá con la página de Wikipedia del torneo, o pegá el fixture a mano."), ""
    nota = "torneo ida y vuelta" if doble else "una sola rueda (si en realidad es ida y vuelta recién arrancado, revisá los «Restan»)"
    return jugados, pend, None, nota

def tabla_desde_url(url):
    """Lee una tabla de posiciones desde una URL (ej. Wikipedia) y la devuelve como texto
    «Equipo, Pts, PJ, DG» listo para el modo tabla. Devuelve (texto, error)."""
    import requests as _rq, io as _io
    try:
        html = _rq.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30).text
    except Exception as e:
        return "", f"No pude descargar la página: {e}"
    try:
        tablas = pd.read_html(_io.StringIO(html))
    except Exception as e:
        return "", f"No encontré tablas legibles en esa página ({e})."
    def _cols(t):
        if isinstance(t.columns, pd.MultiIndex):
            return [_zlow(str(c[-1])) for c in t.columns]
        return [_zlow(str(c)) for c in t.columns]
    def _busca(cols, nombres):
        for i, c in enumerate(cols):
            if c in nombres:
                return i
        return None
    mejor, mejor_score = None, -1
    for t in tablas:
        cols = _cols(t)
        i_pts = _busca(cols, {"pts", "pts.", "puntos"})
        i_pj = _busca(cols, {"pj", "j", "jug", "jj", "part"})
        i_dg = _busca(cols, {"dg", "dif", "dif.", "+/-", "dif. de gol", "dg.", "dif de gol"})
        i_eq = _busca(cols, {"equipo", "club", "team", "equipos"})
        if i_eq is None:
            for i in range(len(cols)):
                if t.dtypes.iloc[i] == object:
                    i_eq = i; break
        score = (i_pts is not None) * 4 + (i_pj is not None) * 2 + (i_dg is not None) + (len(t) >= 6)
        if i_pts is not None and i_eq is not None and score > mejor_score:
            mejor, mejor_score = (t, i_eq, i_pts, i_pj, i_dg), score
    if not mejor:
        return "", "No encontré una tabla con columna de puntos. Probá con la página de Wikipedia del torneo."
    t, i_eq, i_pts, i_pj, i_dg = mejor
    lineas = []
    for _, row in t.iterrows():
        raw = str(row.iloc[i_eq]).strip()
        name = re.sub(r"\s*\[[^\]]*\]", "", raw)
        name = re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()
        if not name or name.lower() in ("nan", "equipo", "club"):
            continue
        def _num(i, defecto=0):
            if i is None: return defecto
            m = re.search(r"[+-]?\d+", str(row.iloc[i]))
            return int(m.group()) if m else None
        pts = _num(i_pts, None)
        if pts is None:
            continue
        pj = _num(i_pj, 0) or 0
        dg = _num(i_dg, 0) or 0
        lineas.append(f"{name}, {pts}, {pj}, {dg:+d}")
    if len(lineas) < 4:
        return "", "Leí la tabla pero con muy pocos equipos válidos. Revisá la URL."
    return "\n".join(lineas), None

def traer_de_apify(token, actor, input_json, timeout=120):
    """Corre un actor de Apify en modo sync y devuelve los items del dataset (lista de dicts)."""
    import requests as _rq, json as _json
    act = (actor or "").strip().replace("/", "~")
    if not act:
        raise ValueError("Indicá el actor (ej.: crawlerbros/flashscore-scraper).")
    try:
        inp = _json.loads(input_json) if str(input_json or "").strip() else {}
    except Exception:
        raise ValueError("El input del actor no es JSON válido.")
    url = f"https://api.apify.com/v2/acts/{act}/run-sync-get-dataset-items?token={token}&format=json"
    r = _rq.post(url, json=inp, timeout=timeout)
    if r.status_code >= 400:
        raise RuntimeError(f"Apify respondió {r.status_code}: {r.text[:300]}")
    data = r.json()
    if isinstance(data, dict):
        for k in ("items", "data"):
            if isinstance(data.get(k), list):
                return data[k]
    return data if isinstance(data, list) else []

def _match_eq(nombre, equipos):
    """Empareja un nombre externo (Flashscore/SofaScore) con los equipos ya cargados, tolerando variantes."""
    nn = _zlow(nombre)
    for e in equipos:
        if _zlow(e) == nn:
            return e
    for e in equipos:
        ee = _zlow(e)
        if ee in nn or nn in ee:
            return e
    tn = set(nn.split())
    mejor, score = None, 0
    for e in equipos:
        s = len(tn & set(_zlow(e).split()))
        if s > score:
            mejor, score = e, s
    return mejor if score else None

def mapear_fixture(pend, equipos):
    out, caidos = [], []
    for a, b in pend:
        ma, mb = _match_eq(a, equipos), _match_eq(b, equipos)
        if ma and mb and ma != mb:
            out.append((ma, mb))
        else:
            caidos.append(f"{a} vs {b}")
    return out, caidos

def importar_partidos_json(texto, filtro=""):
    """Convierte un export de Apify (JSON/NDJSON/CSV) u otra fuente en (jugados, pendientes, ligas, error).
    Reconoce homeTeam/awayTeam/homeScore/awayScore/status/league-tournament con varios alias."""
    import json as _json, csv as _csv, io as _io
    txt = (texto or "").strip()
    if not txt:
        return [], [], {}, "Pegá el contenido exportado (JSON o CSV)."
    recs = []
    try:
        data = _json.loads(txt)
        if isinstance(data, dict):
            for k in ("items", "data", "results", "matches"):
                if isinstance(data.get(k), list):
                    data = data[k]; break
        if isinstance(data, list):
            recs = [r for r in data if isinstance(r, dict)]
    except Exception:
        nd = []
        for ln in txt.splitlines():
            ln = ln.strip().rstrip(",")
            if ln.startswith("{") and ln.endswith("}"):
                try: nd.append(_json.loads(ln))
                except Exception: pass
        recs = nd
    if not recs and ("," in txt or ";" in txt):
        try:
            head = txt.splitlines()[0]
            delim = ";" if head.count(";") > head.count(",") else ","
            recs = [dict(r) for r in _csv.DictReader(_io.StringIO(txt), delimiter=delim)]
        except Exception:
            recs = []
    if not recs:
        return [], [], {}, "No reconocí el formato. Pegá el JSON del actor (lista de partidos) o un CSV con encabezado."
    def pick(r, *keys):
        low = {str(k).lower(): v for k, v in r.items()}
        for k in keys:
            v = low.get(k.lower())
            if v not in (None, ""):
                return v
        return None
    fl = _zlow(filtro or "")
    jugados, pendientes, ligas = [], [], {}
    for r in recs:
        liga = str(pick(r, "league", "tournament", "liga", "competition", "torneo") or "").strip()
        if liga:
            ligas[liga] = ligas.get(liga, 0) + 1
        if fl and fl not in _zlow(liga):
            continue
        h = pick(r, "homeTeam", "home_team", "home", "local", "homeName")
        a = pick(r, "awayTeam", "away_team", "away", "visitante", "awayName")
        if not h or not a:
            continue
        h, a = str(h).strip(), str(a).strip()
        hs, asn = pick(r, "homeScore", "home_score", "golesLocal"), pick(r, "awayScore", "away_score", "golesVisitante")
        stt = _zlow(str(pick(r, "status", "estado") or ""))
        try:
            hs, asn = int(str(hs).strip()), int(str(asn).strip())
        except Exception:
            hs = asn = None
        fin = any(w in stt for w in ("finish", "final", "termin", "ended", "after", "ft"))
        if hs is not None and asn is not None and (fin or not stt):
            jugados.append((h, a, hs, asn))
        elif not any(w in stt for w in ("postpon", "cancel", "aband", "suspend", "walkover", "aplaz")):
            pendientes.append((h, a))
    return jugados, pendientes, ligas, ""

# ── TABLERO DE MEJORES TERCEROS (Mundial 2026: clasifican 8 de 12) ──

def terceros_data(grupos):
    """grupos: {label: (eqs, jug, pen)} → terceros de cada grupo ordenados por pts, DG, GF (criterio FIFA)."""
    rows = []
    for lab, (eqs, jug, pen) in sorted(grupos.items()):
        t = tabla(eqs, jug)
        if len(t) < 3:
            continue
        r = t.iloc[2]
        rest = _restantes(eqs, pen)
        rows.append({"Grupo": lab, "Equipo": r["Equipo"], "PTS": int(r["PTS"]), "DG": int(r["DG"]),
                     "GF": int(r["GF"]), "PJ": int(r["PJ"]), "Restan": int(rest.get(r["Equipo"], 0))})
    rows.sort(key=lambda d: (-d["PTS"], -d["DG"], -d["GF"]))
    return rows

def terceros_texto(grupos, corte=None):
    corte = MEJORES_TERCEROS() if corte is None else corte
    rows = terceros_data(grupos)
    if len(rows) < 2:
        return ("Para el tablero de terceros necesito el **torneo completo** cargado (todos los grupos): "
                "traelo por la API football-data o pegá todos los grupos juntos.")
    L = [f"**Tablero de mejores terceros (si terminara hoy)** — clasifican los mejores **{corte}** de {len(rows)}:"]
    for i, d in enumerate(rows, 1):
        icon = "🟢" if i <= corte else "🔴"
        cola = f" · le quedan {d['Restan']}" if d["Restan"] else ""
        L.append(f"{icon} {i}. **{d['Equipo']}** (Grupo {d['Grupo']}) — {d['PTS']} pts, DG {d['DG']:+d}, GF {d['GF']}{cola}")
    if 0 < corte < len(rows):
        a, f = rows[corte - 1], rows[corte]
        L.append(f"**La línea de corte:** hoy el último que entra es **{a['Equipo']}** ({a['PTS']} pts, DG {a['DG']:+d}) "
                 f"y el primero que queda afuera, **{f['Equipo']}** ({f['PTS']} pts, DG {f['DG']:+d}).")
    L.append("_Criterio FIFA entre terceros: puntos, diferencia de gol y goles a favor. "
             "Es la foto de hoy: se mueve con cada resultado de cualquier grupo — por eso «depende de otros grupos»._")
    return "\n\n".join(L)

def placa_terceros_png(grupos, corte=None):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
    from io import BytesIO
    corte = MEJORES_TERCEROS() if corte is None else corte
    rows = terceros_data(grupos)
    if len(rows) < 2:
        return None
    n = len(rows)
    fig, ax = plt.subplots(figsize=(8.0, 0.62 * n + 1.5), dpi=200)
    ax.set_xlim(0, 12); ax.set_ylim(0, n + 0.7); ax.axis("off")
    ax.set_title(f"Los mejores terceros · hoy  (clasifican {corte} de {n})", fontsize=14.5,
                 fontweight="bold", color="#1a1a2e", loc="left", pad=12)
    for c, x, wca in [("#", 0.35, None), ("Equipo", 1.0, None), ("Grupo", 6.1, None),
                      ("PTS", 7.9, None), ("DG", 9.2, None), ("GF", 10.4, None), ("Restan", 11.55, None)]:
        ax.text(x, n + 0.35, c, ha="left" if x < 6 else "center", va="center",
                fontsize=9.5, fontweight="bold", color="#666")
    for i, d in enumerate(rows, 1):
        y = n - i + 0.5
        col = "#e6f0e6" if i <= corte else "#f7e7e7"
        borde = "#1b5e20" if i <= corte else "#b71c1c"
        ax.add_patch(FancyBboxPatch((0.1, y - 0.27), 11.8, 0.54, boxstyle="round,pad=0.02,rounding_size=0.06",
                                    facecolor=col, edgecolor="none"))
        ax.add_patch(FancyBboxPatch((0.1, y - 0.27), 0.12, 0.54, boxstyle="square,pad=0",
                                    facecolor=borde, edgecolor="none"))
        ax.text(0.42, y, str(i), ha="left", va="center", fontsize=10.5, fontweight="bold", color="#1a1a2e")
        ax.text(1.0, y, d["Equipo"], ha="left", va="center", fontsize=11, fontweight="bold", color="#1a1a2e")
        ax.text(6.1, y, d["Grupo"], ha="center", va="center", fontsize=10.5, color="#1a1a2e")
        ax.text(7.9, y, str(d["PTS"]), ha="center", va="center", fontsize=11, fontweight="bold", color="#1a1a2e")
        ax.text(9.2, y, f"{d['DG']:+d}", ha="center", va="center", fontsize=10.5, color="#1a1a2e")
        ax.text(10.4, y, str(d["GF"]), ha="center", va="center", fontsize=10.5, color="#1a1a2e")
        ax.text(11.55, y, str(d["Restan"]), ha="center", va="center", fontsize=10.5, color="#666")
        if i == corte and corte < n:
            ax.plot([0.1, 11.9], [y - 0.36, y - 0.36], color="#1a1a2e", lw=2.4, ls=(0, (5, 3)))
            ax.text(11.9, y - 0.36, " corte", ha="left", va="center", fontsize=8.5, color="#1a1a2e", style="italic")
    fig.text(0.01, -0.015, "Criterio FIFA: puntos, diferencia de gol y goles a favor. Foto de hoy.",
             fontsize=8.5, style="italic", color="#666")
    buf = BytesIO(); fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white", pad_inches=0.25); plt.close(fig)
    return buf.getvalue()

# ── PROMEDIOS (descenso a la argentina: puntos ÷ partidos de las últimas temporadas) ──

def parse_promedios(texto):
    """Líneas «Equipo, pts, pj» o «Equipo, pts1, pj1, pts2, pj2» (temporadas PREVIAS; se suman).
    La temporada actual la toma sola de la tabla cargada. Devuelve {equipo: (pts_prev, pj_prev)}."""
    out = {}
    for ln in (texto or "").splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        partes = [p.strip() for p in re.split(r"[;,\t]|\s{2,}", ln) if p.strip()]
        if len(partes) < 3:
            continue
        nombre = partes[0]
        nums = [int(p) for p in partes[1:] if re.fullmatch(r"[+-]?\d+", p)]
        if len(nums) < 2:
            continue
        nums = nums[: (len(nums) // 2) * 2]
        pts, pj = sum(nums[0::2]), sum(nums[1::2])
        if pj > 0 and nombre:
            out[nombre] = (pts, pj)
    return out

def _prom_rangos(base, rest, prev):
    """Por equipo: (promedio_hoy, piso = perdiendo todo, techo = ganando todo). Empareja nombres tolerante."""
    eqs = list(base.keys())
    mapped = {}
    for nombre, (pp, jp) in (prev or {}).items():
        m = _match_eq(nombre, eqs)
        if m:
            mapped[m] = (pp, jp)
    out = {}
    for e in eqs:
        pa, ja = base[e]["pts"], base[e].get("pj", 0)
        pp, jp = mapped.get(e, (0, 0))
        tp, tj = pa + pp, ja + jp
        r = rest.get(e, 0)
        hoy = tp / tj if tj else 0.0
        piso = tp / (tj + r) if (tj + r) else 0.0
        techo = (tp + 3 * r) / (tj + r) if (tj + r) else 0.0
        out[e] = {"hoy": hoy, "piso": piso, "techo": techo, "tp": tp, "tj": tj, "r": r, "con_prev": e in mapped}
    return out

def promedios_df(base, rest, prev):
    P = _prom_rangos(base, rest, prev)
    rows = [{"Equipo": e, "Pts (total)": d["tp"], "PJ (total)": d["tj"], "Promedio": round(d["hoy"], 3),
             "Piso": round(d["piso"], 3), "Techo": round(d["techo"], 3),
             "Previas": "sí" if d["con_prev"] else "solo actual"} for e, d in P.items()]
    df = pd.DataFrame(rows).sort_values("Promedio", ascending=False).reset_index(drop=True)
    df.insert(0, "Pos", range(1, len(df) + 1))
    return df

def promedio_que_necesita_texto(e, base, rest, prev, k=1):
    if e not in base:
        return f"No encuentro a {e} en la tabla cargada."
    P = _prom_rangos(base, rest, prev)
    n = len(P); d = P[e]
    df = promedios_df(base, rest, prev); pos = int(df[df["Equipo"] == e]["Pos"].iloc[0])
    abajo_seguro = sorted([x for x in P if x != e and P[x]["techo"] < d["piso"]], key=lambda x: P[x]["techo"])
    arriba_seguro = sorted([x for x in P if x != e and P[x]["piso"] > d["techo"]], key=lambda x: -P[x]["piso"])
    L = [f"**¿{e} y el descenso por promedios?** (descienden los {k} peores)",
         f"Está {pos}º de {n} con promedio **{d['hoy']:.3f}** ({d['tp']} pts en {d['tj']} PJ, contando temporadas previas). "
         f"Perdiendo todo baja a {d['piso']:.3f}; ganando todo sube a {d['techo']:.3f}."]
    if len(abajo_seguro) >= k:
        muestra = ", ".join(abajo_seguro[:4])
        L.append(f"✅ **Ya está a salvo del promedio**: aunque pierda todo lo que le queda, {muestra} "
                 f"no lo pueden superar ni ganando todo (sus techos quedan por debajo de tu piso).")
    elif len(arriba_seguro) >= n - k:
        L.append(f"❌ **Condenado por promedio**: aun ganando todo llega a {d['techo']:.3f} y ya hay "
                 f"{len(arriba_seguro)} equipos que ni perdiendo todo bajan de ese número.")
    else:
        pelea = sorted([x for x in P if x != e and not (P[x]["techo"] < d["piso"]) and not (P[x]["piso"] > d["techo"])],
                       key=lambda x: P[x]["hoy"])
        techos = sorted((P[x]["techo"] for x in P if x != e))
        objetivo = techos[k - 1] if len(techos) >= k else 0.0
        den = d["tj"] + d["r"]
        need = objetivo * den - d["tp"]
        import math
        pts_need = max(0, math.ceil(need + 1e-9))
        if pelea:
            L.append("⚔️ **Pelea mano a mano con:** " + ", ".join(pelea[:6]) + ".")
        if d["r"] and pts_need <= 3 * d["r"]:
            L.append(f"Para salvarse **sin depender de nadie** necesita sumar **{pts_need} pts** de los {3*d['r']} en juego "
                     f"(así su promedio supera el techo del {k}º peor).")
        else:
            L.append("Ni ganando todo se asegura solo: necesita sumar **y** que los de abajo pinchen.")
    L.append("_Exacto por rangos de promedio (piso y techo). Los recién ascendidos computan solo la temporada actual: así es la regla. "
             "Cargá las temporadas previas en el panel «📉 Promedios»._")
    return "\n\n".join(L)

def panorama(equipos, jugados, esc, directo=None):
    d = DIRECTO() if directo is None else directo; hay3 = MEJORES_TERCEROS() > 0
    filas = []
    for e in equipos:
        s = situacion(e, esc, d)
        if s["ya_directo"]: est = "🟢 Clasificado directo"
        elif s["eliminado"]: est = "🔴 Eliminado"
        elif s["puede_directo"]: est = "🟡 En disputa"
        elif hay3: est = "🔵 Chance vía mejor 3º"
        else: est = "🔴 Eliminado"
        filas.append({"Equipo": e, "Estado": est, "Mejor": s["mejor"], "Peor": s["peor"],
                      "Puede 1º": "sí" if s["puede_1"] else "no",
                      "Directo en": f"{s['ndir']}/{s['total']}"})
    orden = {r["Equipo"]: r["Pos"] for _, r in tabla(equipos, jugados).iterrows()}
    return pd.DataFrame(filas).sort_values("Equipo", key=lambda c: c.map(orden)).reset_index(drop=True)

def _desc_obj(o):
    return {"exacto": f"exactamente {o[1]}º", "al_menos": f"{o[1]}º o mejor",
            "como_mucho": f"{o[1]}º o peor", "entre": f"entre {o[1]}º y {o[-1]}º"}[o[0]]

def _ok_pos(pos, o):
    if o[0] == "exacto":    return pos == o[1]
    if o[0] == "al_menos":  return pos <= o[1]
    if o[0] == "como_mucho":return pos >= o[1]
    return (pos >= o[1]) & (pos <= o[2])

def resultados_para_puesto_texto(equipo, esc, pend, objetivo):
    pos = esc[f"Pos {equipo}"]; ok = _ok_pos(pos, objetivo); desc = _desc_obj(objetivo)
    n, tot = int(ok.sum()), len(esc)
    if n == 0:
        alc = ", ".join(f"{int(p)}º" for p in sorted(pos.unique()))
        return f"❌ **IMPOSIBLE**: {equipo} no puede terminar {desc}.\n\nPuestos alcanzables: {alc}."
    if n == tot:
        return f"✅ {equipo} termina {desc} **pase lo que pase**."
    df = esc.copy(); df["_c"] = df.apply(lambda r: _combo(r, pend), axis=1); df["_ok"] = ok.values
    siempre, aveces = [], []
    for c, g in df.groupby("_c"):
        k, m = int(g["_ok"].sum()), len(g)
        if k == m: siempre.append(c)
        elif k > 0: aveces.append((c, k, m))
    lineas = []
    if siempre:
        lineas.append("**Lo logra SIEMPRE con:**")
        for c in siempre: lineas.append(f"✅ {c}")
    if aveces:
        lineas.append("\n**Lo logra SOLO si la dif. de gol acompaña:**")
        for c, k, m in sorted(aveces, key=lambda x: -x[1]/x[2]):
            lineas.append(f"⚠️ {c} &nbsp;({k}/{m} marcadores)")
    return "\n\n".join(lineas)

def probabilidades(equipos, jugados, pendientes, n=8000, media=1.3, fuerza=None, seed=1):
    rng = np.random.default_rng(seed)
    lam = {e: media * (fuerza.get(e, 1.0) if fuerza else 1.0) for e in equipos}
    cuenta = {e: np.zeros(len(equipos) + 1, dtype=int) for e in equipos}
    base = list(jugados)
    for _ in range(n):
        part = base + [(l, v, int(rng.poisson(lam[l] * 1.12)), int(rng.poisson(lam[v] * 0.92))) for (l, v) in pendientes]
        for e, p in posiciones(equipos, part).items(): cuenta[e][p] += 1
    rows = [{"Equipo": e, "1º %": round(100 * cuenta[e][1] / n, 1),
             "Top 2 %": round(100 * cuenta[e][1:3].sum() / n, 1),
             "Top 3 %": round(100 * cuenta[e][1:4].sum() / n, 1)} for e in equipos]
    return pd.DataFrame(rows).sort_values("Top 2 %", ascending=False).reset_index(drop=True)

def que_pasa_si(esc, pend, condiciones, equipos):
    mask = pd.Series(True, index=esc.index)
    for i, cond in enumerate(condiciones, 1):
        if not cond: continue
        gl, gv = esc[f"P{i}_gl"], esc[f"P{i}_gv"]
        mask &= (gl > gv) if cond == "L" else (gl == gv) if cond == "E" else (gl < gv)
    sub = esc[mask]
    rows = [{"Equipo": e, "Mejor": int(sub[f"Pos {e}"].min()), "Peor": int(sub[f"Pos {e}"].max()),
             "Directo posible": "sí" if (sub[f"Pos {e}"] <= 2).any() else "no",
             "Directo seguro": "sí" if (sub[f"Pos {e}"] <= 2).all() else "no"} for e in equipos]
    return sub, pd.DataFrame(rows)

def distribucion(equipos, esc):
    d = pd.DataFrame({e: esc[f"Pos {e}"].value_counts() for e in equipos}).fillna(0).astype(int).sort_index()
    d.index.name = "Puesto"; return d

def _restantes(equipos, pend):
    r = {e: 0 for e in equipos}
    for l, v in pend: r[l] += 1; r[v] += 1
    return r

def maximos_minimos(equipos, jugados, pend):
    ov = _stats(equipos, jugados); rest = _restantes(equipos, pend)
    rows = [{"Equipo": e, "PJ": ov[e]["pj"], "PTS": ov[e]["pts"], "Restan": rest[e],
             "PTS máx": ov[e]["pts"] + 3 * rest[e]} for e in equipos]
    return pd.DataFrame(rows).sort_values(["PTS", "PTS máx"], ascending=False).reset_index(drop=True)

def clasificado_eliminado(equipos, jugados, pend, n=1):
    ov = _stats(equipos, jugados); rest = _restantes(equipos, pend)
    pts = {e: ov[e]["pts"] for e in equipos}; pmax = {e: pts[e] + 3 * rest[e] for e in equipos}
    col = CAMPEON().capitalize() if n == 1 else f"Top {n}"
    rows = []
    for e in equipos:
        arriba = sum(1 for x in equipos if x != e and pmax[x] > pts[e])
        inalc  = sum(1 for x in equipos if x != e and pts[x] > pmax[e])
        estado = "🟢 asegurado" if arriba < n else ("🔴 sin chances" if inalc >= n else "🟡 depende")
        rows.append({"Equipo": e, "PTS": pts[e], "PTS máx": pmax[e], col: estado})
    return pd.DataFrame(rows).sort_values("PTS", ascending=False).reset_index(drop=True)

def numero_magico_texto(equipo, equipos, jugados, pend, n=1):
    ov = _stats(equipos, jugados); rest = _restantes(equipos, pend)
    pts = {e: ov[e]["pts"] for e in equipos}; pmax = {e: pts[e] + 3 * rest[e] for e in equipos}
    otros = sorted((pmax[x] for x in equipos if x != equipo), reverse=True)
    meta = f"ser {CAMPEON()}" if n == 1 else f"entrar al top {n}"
    lineas = [f"**{equipo}** — para {meta}:",
              f"Tiene **{pts[equipo]} pts** y le quedan {rest[equipo]} partidos ({3*rest[equipo]} en juego)."]
    if len(otros) < n:
        lineas.append(f"✅ Ya está en el top {n}.")
    else:
        necesita = max(0, (otros[n-1] + 1) - pts[equipo]); tope = 3 * rest[equipo]
        if necesita == 0:
            lineas.append("✅ Ya está asegurado pase lo que pase.")
        elif necesita <= tope:
            lineas.append(f"Necesita sumar **{necesita} pts** más para asegurarlo sin depender de nadie.")
        else:
            lineas.append(f"No puede asegurarlo solo: necesitaría {necesita} y solo hay {tope} en juego → depende de que los rivales pinchen.")
    pq = _porque_numero_magico(equipo, equipos, jugados, pend, n)
    if pq:
        lineas.append("🔍 **Por qué:** " + pq)
    return "\n\n".join(lineas)

def mejor_resultado_texto(equipo, esc, pend, directo=None):
    d = DIRECTO() if directo is None else directo
    df = esc.copy(); df["_p"] = df.apply(lambda r: _res_propio(r, equipo, pend), axis=1)
    rk = lambda p: 0 if p.startswith("le gana") else (1 if p.startswith("empata") else 2)
    opciones = []
    for prop, g in df.groupby("_p"):
        gp = esc.loc[g.index, f"Pos {equipo}"]
        opciones.append({"r": prop, "peor": int(gp.max()), "mejor": int(gp.min()),
                         "prom": float(gp.mean()), "uno": int((gp == 1).sum()),
                         "dir": int((gp <= d).sum()), "n": len(g), "rk": rk(prop)})
    opciones.sort(key=lambda o: (round(o["prom"], 6), o["peor"], o["mejor"], o["rk"]))
    lineas = []
    for i, o in enumerate(opciones):
        flag = " 👍 lo que más le conviene" if i == 0 else ""
        lineas.append(f"• Si {equipo} **{o['r']}**: termina entre {o['mejor']}º y {o['peor']}º · "
                      f"sale 1º en {o['uno']}/{o['n']} · clasifica directo en {o['dir']}/{o['n']}{flag}")
    return "\n\n".join(lineas)

def _gana_todo(p): return bool(p) and all(s.startswith("le gana") for s in p.split(" y "))

def conviene_otros_texto(equipo, esc, pend, directo=None):
    """Qué le conviene al equipo en los partidos que NO juega."""
    d = DIRECTO() if directo is None else directo
    otros_pend = [p for p in pend if equipo not in p]
    if not otros_pend:
        return ""
    df = esc.copy()
    df["_p"] = df.apply(lambda r: _res_propio(r, equipo, pend), axis=1)
    df["_o"] = df.apply(lambda r: _res_otros(r, equipo, pend), axis=1)
    if _pd_de(equipo, pend):
        sub = df[df["_p"].map(_gana_todo)]
        cab = f"Si **{equipo} gana lo suyo**, le conviene en los otros partidos (de mejor a peor):"
        if sub.empty: sub, cab = df, f"A **{equipo}** le conviene en los otros partidos (de mejor a peor):"
    else:
        sub, cab = df, f"A **{equipo}** le conviene en los otros partidos (de mejor a peor):"
    rows = []
    for o, g in sub.groupby("_o"):
        gp = esc.loc[g.index, f"Pos {equipo}"]
        rows.append({"o": o, "prom": float(gp.mean()), "uno": int((gp == 1).sum()),
                     "dir": int((gp <= d).sum()), "n": len(g)})
    rows.sort(key=lambda r: (round(r["prom"], 6), -r["dir"] / r["n"]))
    lineas = [cab]
    for i, r in enumerate(rows):
        flag = " 👍" if i == 0 else ""
        lineas.append(f"• Que {r['o']}: sale 1º en {r['uno']}/{r['n']} · clasifica directo en {r['dir']}/{r['n']}{flag}")
    return "\n\n".join(lineas)

def combo_ideal_texto(equipo, esc, pend, directo=None):
    """Cierra el 'conviene' con el combo ideal: lo propio + lo de los otros en una frase."""
    d = DIRECTO() if directo is None else directo
    if not pend:
        return ""
    pos = esc[f"Pos {equipo}"]; best = int(pos.min())
    mios = _pd_de(equipo, pend)
    df = esc.copy(); df["_p"] = df.apply(lambda r: _res_propio(r, equipo, pend), axis=1)
    verd = "sale 1º" if best == 1 else (f"clasifica (termina {best}º)" if best <= d else f"termina {best}º")
    # ¿algún resultado propio garantiza el mejor puesto sin depender de nadie?
    solo = None
    if mios:
        for prop, g in df.groupby("_p"):
            gp = esc.loc[g.index, f"Pos {equipo}"]
            if int(gp.max()) == best:
                if solo is None or prop.startswith("le gana"):
                    solo = prop
    if solo:
        return f"🎯 **Escenario ideal de {equipo}:** que **{solo}** — con eso {verd} sin depender de nadie."
    # combinar: elegir el mejor resultado propio (preferir ganar) y, dentro, un combo de otros que logre 'best'
    cand = []
    for prop, g in df.groupby("_p"):
        gp = esc.loc[g.index, f"Pos {equipo}"]
        cand.append((int(gp.min()), 0 if prop.startswith("le gana") else (1 if prop.startswith("empata") else 2), prop, g.index))
    cand.sort()
    _, _, prop_best, idx = cand[0]
    sub = esc.loc[idx]
    sub = sub[sub[f"Pos {equipo}"] == best]
    if len(sub) == 0:
        return ""
    row = esc.loc[sub.index[0]]
    otros = _res_otros(row, equipo, pend)
    if mios and otros and otros != "(no hay otros partidos)":
        return f"🎯 **Escenario ideal de {equipo}:** que **{prop_best}** y que en los otros **{otros}** → así {verd}."
    if mios:
        return f"🎯 **Escenario ideal de {equipo}:** que **{prop_best}** → así {verd}."
    return f"🎯 **Escenario ideal de {equipo}:** que en los otros partidos **{_combo(row, pend)}** → así {verd}."

def _efecto_eq(team, sub, d, hay3):
    pos = sub[f"Pos {team}"]; rd = float((pos <= d).mean())
    if rd >= 0.999:
        return "termina 1º" if float((pos == 1).mean()) >= 0.999 else "clasifica"
    if rd <= 0.001:
        if hay3 and float((pos == 3).mean()) > 0:
            return "queda a pelear el 3º"
        return "queda afuera"
    return "queda a depender"

def _match_define(a, b, esc, i, d, hay3):
    teams = []
    for t in (a, b):
        efs = set()
        for res in ("L", "E", "V"):
            sub = filtrar_esc(esc, {i: res})
            if len(sub):
                efs.add(_efecto_eq(t, sub, d, hay3))
        if len(efs) > 1:
            teams.append(t)
    return teams

def previa_fecha_texto(eqs, jug, esc, pend):
    d = DIRECTO(); hay3 = MEJORES_TERCEROS() > 0
    if not pend:
        return "No quedan partidos: el grupo ya está definido."
    sc = bisagra_scores(eqs, jug, pend, esc)
    L = ["**Previa de la fecha — qué se define en cada partido:**"]
    for s in sc:
        a, b = s["match"]; afect = _match_define(a, b, esc, s["i"], d, hay3)
        head = ("define la clasificación de " + ", ".join(afect)) if afect else "incide solo en el desempate"
        L.append(f"\n**{a} vs {b}** — {head}.")
        for res, lbl in [("L", f"Gana {a}"), ("E", "Empate"), ("V", f"Gana {b}")]:
            sub = filtrar_esc(esc, {s["i"]: res})
            if len(sub) == 0:
                continue
            L.append(f"- {lbl}: {a} {_efecto_eq(a, sub, d, hay3)}; {b} {_efecto_eq(b, sub, d, hay3)}.")
    return "\n\n".join(L)

def placa_previa_fecha_png(eqs, jug, esc, pend, etiqueta=""):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
    from io import BytesIO
    d = DIRECTO(); hay3 = MEJORES_TERCEROS() > 0
    sc = bisagra_scores(eqs, jug, pend, esc)
    if not sc:
        return None
    nblocks = len(sc); rows = nblocks * 4
    fig, ax = plt.subplots(figsize=(8.4, 0.52 * rows + 1.2), dpi=200)
    ax.set_xlim(0, 12); ax.set_ylim(0, rows); ax.axis("off")
    titulo = "Previa de la fecha: ¿qué define cada partido?" + (f"  ·  Grupo {etiqueta}" if etiqueta else "")
    ax.set_title(titulo, fontsize=14.5, fontweight="bold", color="#1a1a2e", loc="left", pad=12)
    y = rows
    colmap = {"L": "#1b5e20", "E": "#9e9e9e", "V": "#1b5e20"}
    import textwrap
    for s in sc:
        a, b = s["match"]; afect = _match_define(a, b, esc, s["i"], d, hay3)
        head = ("Define la clasificación de " + ", ".join(afect)) if afect else "Incide solo en el desempate"
        y -= 1
        ax.add_patch(FancyBboxPatch((0.1, y + 0.08), 11.8, 0.86, boxstyle="round,pad=0.02,rounding_size=0.08",
                                    facecolor="#1a1a2e", edgecolor="none"))
        ax.text(0.35, y + 0.62, f"{a} vs {b}", ha="left", va="center", color="white", fontsize=11.5, fontweight="bold")
        ax.text(0.35, y + 0.27, head, ha="left", va="center", color="#cfe3cf", fontsize=9, style="italic")
        for res, lbl in [("L", f"Gana {a}"), ("E", "Empate"), ("V", f"Gana {b}")]:
            sub = filtrar_esc(esc, {s["i"]: res}); y -= 1
            if len(sub) == 0:
                continue
            ax.add_patch(FancyBboxPatch((0.3, y + 0.1), 3.3, 0.78, boxstyle="round,pad=0.02,rounding_size=0.08",
                                        facecolor=colmap[res], edgecolor="none"))
            lbl_w = "\n".join(textwrap.wrap(lbl, 16))
            fs = 10.5 if len(lbl) <= 14 else 9
            ax.text(1.95, y + 0.5, lbl_w, ha="center", va="center", color="white", fontsize=fs, fontweight="bold")
            ax.text(3.85, y + 0.5, f"{a} {_efecto_eq(a, sub, d, hay3)}  ·  {b} {_efecto_eq(b, sub, d, hay3)}",
                    ha="left", va="center", color="#1a1a2e", fontsize=10.5)
    buf = BytesIO(); fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white", pad_inches=0.25); plt.close(fig)
    return buf.getvalue()

def _frase_equipo(equipo, eqs, jug, esc, pend):
    s = situacion(equipo, esc); hay3 = MEJORES_TERCEROS() > 0
    if s["ya_directo"]:
        if s.get("ya_1"): return "ya está 1º y clasificado."
        if s.get("puede_1"): return "ya clasificado; todavía pelea el 1º."
        return "ya clasificado."
    if s["eliminado"]:
        return "ya sin chances."
    br = arbol_branches(equipo, eqs, jug, esc, pend)
    if not br:
        cat, manos = en_sus_manos(equipo, esc, pend)
        return manos + "."
    vd = {}
    for b in br:
        lab = b["label"].lower()
        if lab.startswith("le gana"): vd["G"] = b["verd"]
        elif lab.startswith("empata"): vd["E"] = b["verd"]
        elif lab.startswith("pierde"): vd["P"] = b["verd"]
    G, E, P = vd.get("G"), vd.get("E"), vd.get("P")
    if E == "Clasifica":
        if G == "Clasifica" and s.get("puede_1"):
            return "con un empate ya pasa; ganando puede ser 1º."
        return "le alcanza con un empate."
    if G == "Clasifica":
        if E == "Depende":
            return "gana y pasa; si empata, queda a depender de otros."
        if "Pelea 3º" in (E, P):
            return "gana y pasa; si no, a esperar como mejor 3º."
        return "tiene que ganar para clasificar."
    if G == "Depende":
        return "ni ganando se asegura: necesita ganar y que lo ayuden."
    if G == "Pelea 3º":
        return "fuera de los 2 primeros; se juega la chance de mejor 3º."
    return "complicado: necesita ganar y esperar resultados."

def que_se_juega_texto(eqs, jug, esc, pend):
    t = tabla(eqs, jug)
    L = ["**Qué se juega cada equipo:**"]
    for _, r in t.iterrows():
        e = r["Equipo"]
        L.append(f"**{e}** ({int(r['PTS'])} pts): {_frase_equipo(e, eqs, jug, esc, pend)}")
    return "\n\n".join(L)

def placa_que_se_juega_png(eqs, jug, esc, pend, etiqueta=""):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
    import textwrap
    from io import BytesIO
    t = tabla(eqs, jug); filas = list(t["Equipo"])
    n = len(filas); fig, ax = plt.subplots(figsize=(8.2, 0.95 * n + 1.2), dpi=200)
    ax.set_xlim(0, 12); ax.set_ylim(0, n); ax.axis("off")
    titulo = "¿Qué se juega cada equipo?" + (f"  ·  Grupo {etiqueta}" if etiqueta else "")
    ax.set_title(titulo, fontsize=15.5, fontweight="bold", color="#1a1a2e", loc="left", pad=12)
    for j, e in enumerate(filas):
        y = n - 0.5 - j
        s = situacion(e, esc)
        col = "#1b5e20" if s["ya_directo"] else ("#b71c1c" if s["eliminado"] else "#37474f")
        ax.add_patch(FancyBboxPatch((0.1, y - 0.38), 3.0, 0.76, boxstyle="round,pad=0.02,rounding_size=0.1",
                                    facecolor=col, edgecolor="none"))
        ax.text(1.6, y, e, ha="center", va="center", color="white", fontsize=11.5, fontweight="bold")
        frase = _frase_equipo(e, eqs, jug, esc, pend)
        ax.text(3.35, y, "\n".join(textwrap.wrap(frase, 52)), ha="left", va="center", fontsize=11, color="#1a1a2e")
    fig.text(0.01, -0.015, "Verde = ya clasificado · Rojo = sin chances · Gris = en juego.", fontsize=8.5, style="italic", color="#666")
    buf = BytesIO(); fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white", pad_inches=0.25); plt.close(fig)
    return buf.getvalue()

def resumen_grupo_texto(equipos, jugados, esc=None, pend=None, directo=None):
    """Pantallazo en texto del grupo: líder, escoltas y estado de la pelea."""
    d = DIRECTO() if directo is None else directo
    t = tabla(equipos, jugados); top = t.iloc[0]
    txt = f"📋 **{top['Equipo']}** lidera con **{int(top['PTS'])} pts**"
    if len(t) > 1: txt += f", escolta {t.iloc[1]['Equipo']} ({int(t.iloc[1]['PTS'])})."
    else: txt += "."
    partes = [txt]
    if pend: partes.append("Falta(n): " + ", ".join(f"{l} vs {v}" for l, v in pend) + ".")
    if esc is not None:
        S = {e: situacion(e, esc, d) for e in equipos}
        clas = [e for e in equipos if S[e]["ya_directo"]]
        elim = [e for e in equipos if S[e]["eliminado"]]
        disp = [e for e in equipos if not S[e]["ya_directo"] and not S[e]["eliminado"]]
        if clas: partes.append("Ya clasificó: " + ", ".join(clas) + ".")
        if elim: partes.append("Sin chances: " + ", ".join(elim) + ".")
        pelean = [e for e in disp if S[e]["puede_directo"]]
        if len(pelean) >= 2 and len(clas) < d:
            partes.append(f"Pelean por entrar: {', '.join(pelean)}.")
        elif disp:
            partes.append("En disputa: " + ", ".join(disp) + ".")
    return " ".join(partes)

def necesita_por_resultados_texto(equipo, equipos, jugados, pendientes, n=None):
    """Para muchos partidos: razona por resultado (G/E/P) y puntos, sin simular goles."""
    n = DIRECTO() if n is None else n
    if not pendientes:
        return "No quedan partidos."
    base = {e: _stats(equipos, jugados)[e]["pts"] for e in equipos}
    mios  = [i for i, p in enumerate(pendientes) if equipo in p]
    otros = [i for i in range(len(pendientes)) if i not in mios]
    meta     = f"ser {CAMPEON()}" if n == 1 else f"clasificar (top {n})"
    verbo_ok = f"es {CAMPEON()}"  if n == 1 else f"entra al top {n}"
    porpts = {}
    for own in product("LEV", repeat=len(mios)):
        add = {e: 0 for e in equipos}
        for k, i in enumerate(mios):
            l, v = pendientes[i]
            if own[k] == "L": add[l] += 3
            elif own[k] == "V": add[v] += 3
            else: add[l] += 1; add[v] += 1
        for oth in product("LEV", repeat=len(otros)):
            final = {e: base[e] + add[e] for e in equipos}
            for k, i in enumerate(otros):
                l, v = pendientes[i]
                if oth[k] == "L": final[l] += 3
                elif oth[k] == "V": final[v] += 3
                else: final[l] += 1; final[v] += 1
            p = final[equipo]
            arriba = sum(1 for x in equipos if x != equipo and final[x] > p)
            igual  = sum(1 for x in equipos if x != equipo and final[x] == p)
            rem    = n - arriba
            porpts.setdefault(p, []).append("safe" if rem >= igual + 1 else ("out" if rem <= 0 else "tie"))
    niveles  = sorted(porpts, reverse=True)
    safe_pts = [p for p in niveles if all(s == "safe" for s in porpts[p])]
    out_pts  = [p for p in niveles if all(s == "out"  for s in porpts[p])]
    medio    = [p for p in niveles if p not in safe_pts and p not in out_pts]
    total_comb = 3 ** len(pendientes)
    lineas = [f"**¿Qué necesita {equipo} para {meta}?** — por resultados ({total_comb:,} combinaciones)\n"]
    if safe_pts:
        lineas.append(f"✅ Con **{min(safe_pts)} pts** o más: {equipo} {verbo_ok} **pase lo que pase**.")
    if medio:
        borde = any("tie" in porpts[p] for p in medio)
        rng = f"{min(medio)} a {max(medio)}" if min(medio) != max(medio) else f"{medio[0]}"
        lineas.append(f"⚠️ Con **{rng} pts**: depende de los otros resultados" +
                      (" (y en algunos casos de la diferencia de gol)" if borde else "") + ".")
    if out_pts:
        lineas.append(f"❌ Con **{max(out_pts)} pts** o menos: no le alcanza.")
    lineas.append("\n_(Se razona por resultados; los empates de puntos por el último cupo se deciden por diferencia de gol.)_")
    return "\n\n".join(lineas)

# ─── TORNEO COMPLETO ─────────────────────────────────────────────────────────────
def analizar_torneo(texto):
    d = DIRECTO(); tablas, terceros, directos, avisos = {}, [], [], []
    for lab, txt in dividir_grupos(texto).items():
        eq, jug, pen = parsear_resultados(txt)
        if len(eq) < 3: avisos.append(f"Grupo {lab}: pocos equipos."); continue
        t = tabla(eq, jug); tablas[lab] = t
        if pen: avisos.append(f"Grupo {lab}: faltan {len(pen)} partido(s) → terceros provisorios.")
        for _, r in t.iterrows():
            if r["Pos"] <= d: directos.append((lab, r["Equipo"], int(r["Pos"])))
            if r["Pos"] == 3: terceros.append((f"{lab} · {r['Equipo']}", int(r["PTS"]), int(r["DG"]), int(r["GF"])))
    def clave(t): return (t[1], t[2], t[3])
    tbl3 = (pd.DataFrame([{"Pos": i, "Grupo": t[0], "PTS": t[1], "DG": t[2], "GF": t[3],
                            "Clasifica": "✅ sí" if i <= MEJORES_TERCEROS() else "❌ no"}
                           for i, t in enumerate(sorted(terceros, key=clave, reverse=True), 1)])
            if terceros and MEJORES_TERCEROS() > 0 else None)
    return tablas, directos, tbl3, avisos

# ─── PARSER ─────────────────────────────────────────────────────────────────────
_MESES = r"(ene|feb|mar|abr|may|jun|jul|ago|sep|set|oct|nov|dic|jan|apr|aug|dec)"
_DIAS  = r"(lun|mar|mié|mie|jue|vie|sáb|sab|dom|mon|tue|wed|thu|fri|sat|sun)"
_RE_SCORE = re.compile(r"^(.+?)\s+(\d{1,2})\s*(?:[-–—xX]\s*(\d{1,2})|:\s*(\d))\s+(.+?)$")
_RE_VS    = re.compile(r"^(.+?)\s+(?:vs?\.?|–|—|-|x)\s+(.+?)$", re.I)

def _limpiar(ln):
    ln = ln.strip()
    pref = [rf"^{_DIAS}\w*\.?,?\s+", r"^\d{1,2}[:.]\d{2}\s+",
            r"^\d{1,2}[/\-.]\d{1,2}([/\-.]\d{2,4})?\s+",
            rf"^\d{{1,2}}\s+{_MESES}\w*\.?,?\s+", rf"^{_MESES}\w*\.?\s+\d{{1,2}},?\s+"]
    ch = True
    while ch:
        ch = False
        for p in pref:
            nu = re.sub(p, "", ln, flags=re.I)
            if nu != ln: ln = nu; ch = True
    ln = re.sub(r"\s*\(.*?\)\s*$", "", ln)
    ln = re.sub(r"\s*(FT|Finalizado|Final|Termin\w*|Ver resumen|Resumen)\s*$", "", ln, flags=re.I)
    return ln.strip()

def _norm(t): return re.sub(r"\s+", " ", t).strip(" -–—\t")
def _let(t):  return bool(re.search(r"[A-Za-zÁÉÍÓÚáéíóúñÑ]", t))

def parsear_resultados(texto):
    jug, pen, eq = [], [], []
    def add(t):
        if t and t not in eq: eq.append(t)
    for raw in texto.splitlines():
        ln = _limpiar(raw)
        if not ln: continue
        m = _RE_SCORE.match(ln)
        if m:
            loc, vis = _norm(m.group(1)), _norm(m.group(5))
            gl = int(m.group(2)); gv = int(m.group(3) if m.group(3) is not None else m.group(4))
            if _let(loc) and _let(vis): add(loc); add(vis); jug.append((loc, vis, gl, gv)); continue
        m = _RE_VS.match(ln)
        if m:
            loc, vis = _norm(m.group(1)), _norm(m.group(2))
            if _let(loc) and _let(vis) and not re.search(r"\d", loc + vis):
                add(loc); add(vis); pen.append((loc, vis))
    jp = {frozenset((l, v)) for l, v, _, _ in jug}
    pp = {frozenset(p) for p in pen}
    for a, b in combinations(eq, 2):
        fs = frozenset((a, b))
        if fs not in jp and fs not in pp: pen.append((a, b)); pp.add(fs)
    return eq, jug, pen

_RE_HEADER = re.compile(r"^\s*(grupo|group|gpo)\s*[:.]?\s*([A-Za-z0-9]+)\s*[:.]?\s*$", re.I)

def dividir_grupos(texto):
    g, act, suelto = {}, None, []
    for ln in texto.splitlines():
        m = _RE_HEADER.match(ln.strip())
        if m: act = m.group(2).upper(); g.setdefault(act, [])
        else: (g[act] if act is not None else suelto).append(ln)
    if not g and any(s.strip() for s in suelto): g["Único"] = suelto
    return {k: "\n".join(v) for k, v in g.items()}

# ─── API ─────────────────────────────────────────────────────────────────────────
_FIN = {"FINISHED", "AWARDED"}

def _grp(lbl): return re.split(r"[ _]", str(lbl).strip())[-1].upper() if lbl else "?"
def _nom(t):   return (t.get("shortName") or t.get("name") or t.get("tla") or "¿?").strip()

def matches_a_texto(matches):
    grupos = {}; liga = []
    for m in matches:
        loc, vis = _nom(m["homeTeam"]), _nom(m["awayTeam"])
        ft = (m.get("score") or {}).get("fullTime") or {}; gl, gv = ft.get("home"), ft.get("away")
        jugado = m.get("status") in _FIN and gl is not None and gv is not None
        linea = f"{loc} {gl}-{gv} {vis}" if jugado else f"{loc} vs {vis}"
        if "GROUP" in str(m.get("stage", "")).upper() or m.get("group"):
            grupos.setdefault(_grp(m.get("group")), []).append(linea)
        elif str(m.get("stage", "")).upper() == "REGULAR_SEASON":
            liga.append(linea)
    out = []
    if grupos:
        for g in sorted(grupos):
            out += [f"Grupo {g}", *grupos[g], ""]
    elif liga:
        out += liga  # liga entera: una sola tabla, sin encabezado de grupo
    return "\n".join(out).strip()

def traer_de_api(token, comp="WC"):
    base = f"https://api.football-data.org/v4/competitions/{comp}"
    h = {"X-Auth-Token": (token or "").strip()}
    r = requests.get(base + "/matches", headers=h, timeout=30)
    if r.status_code == 200:
        return r.json().get("matches", [])
    # football-data manda el motivo real en el cuerpo JSON
    try:
        msg = r.json().get("message", "") or r.text[:200]
    except Exception:
        msg = (r.text or "")[:200]
    # Si falla sin temporada, busco la temporada actual y reintento (útil para copas como el Mundial)
    try:
        info = requests.get(base, headers=h, timeout=30)
        if info.status_code == 200:
            cs = info.json().get("currentSeason") or {}
            yr = str(cs.get("startDate") or "")[:4]
            if yr:
                r2 = requests.get(base + f"/matches?season={yr}", headers=h, timeout=30)
                if r2.status_code == 200:
                    return r2.json().get("matches", [])
                try:
                    msg = r2.json().get("message", "") or msg
                except Exception:
                    pass
    except Exception:
        pass
    raise RuntimeError(f"{r.status_code} — {msg}" if msg else f"{r.status_code} (sin detalle de la API)")

def listar_competiciones(token):
    r = requests.get("https://api.football-data.org/v4/competitions",
                     headers={"X-Auth-Token": token}, timeout=30)
    r.raise_for_status()
    return [(c.get("code"), c.get("name")) for c in r.json().get("competitions", [])]

# ─── HELPER: cargar estado ────────────────────────────────────────────────────────
def cargar_estado(equipos, jugados, pendientes):
    mg = elegir_max_goles(len(pendientes))
    total = (mg+1)**(2*len(pendientes))
    if total > 200000:   # demasiados partidos (liga): no se puede enumerar, vamos por puntos
        st.session_state.ESTADO = dict(equipos=equipos, jugados=jugados, pendientes=pendientes,
                                       esc=None, mg=mg, solo_puntos=True)
        return
    with st.spinner(f"Calculando {total:,} escenarios…"):
        esc = todos_los_escenarios(equipos, jugados, pendientes, mg)
    st.session_state.ESTADO = dict(equipos=equipos, jugados=jugados, pendientes=pendientes,
                                   esc=esc, mg=mg, solo_puntos=False)
    return esc

def _procesar_import(jg, pd_, ligas, filtro, solo_fixture=False):
    """Carga lo importado: como estado completo, o solo como fixture de la liga (tabla) ya cargada."""
    if len(ligas) > 1 and not (filtro or "").strip():
        st.warning("Hay varias ligas en el export. Afiná el filtro con alguna de estas:")
        for lg, cnt in sorted(ligas.items(), key=lambda kv: -kv[1])[:12]:
            st.caption(f"· {lg} ({cnt})")
        return False
    if solo_fixture:
        E = st.session_state.ESTADO
        if not (E and E.get("modo") == "liga_tabla"):
            st.error("Primero cargá la tabla (fuente «Pegar tabla + fixture»)."); return False
        pares, caidos = mapear_fixture(pd_ or [], E["equipos"])
        if not pares:
            st.error("No pude emparejar los partidos con los equipos de tu tabla. Revisá los nombres."); return False
        E["pendientes"] = pares
        E["rest"] = liga_restantes(E["equipos"], pares, None)
        E["gleft"] = None
        st.session_state.ESTADO = E
        st.success(f"Fixture actualizado: {len(pares)} partidos emparejados" +
                   (f" ({len(caidos)} sin emparejar: {', '.join(caidos[:3])}…)" if caidos else " ✓"))
        return True
    eqs_imp = sorted({t for par in ((jg or []) + (pd_ or [])) for t in (par[0], par[1])})
    if len(eqs_imp) < 3:
        st.error("Muy pocos equipos tras el filtro. Revisá el filtro o el export."); return False
    if not jg and not pd_:
        st.error("No encontré partidos válidos tras el filtro."); return False
    cargar_estado(eqs_imp, jg, pd_)
    st.success(f"Importados {len(jg)} resultados y {len(pd_)} por jugar ({len(eqs_imp)} equipos) ✓")
    return True

# ═══════════════════════════════════════════════════════════════════════════════════
# UI
# ═══════════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="main-header">
  <h1>⚽ Calculadora Mundial 2026</h1>
  <p>Análisis de escenarios, clasificación y desempate FIFA por grupo · Mejores terceros</p>
</div>
""", unsafe_allow_html=True)

# ─── SIDEBAR ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("🔧 Configuración")

    # Desempate
    st.subheader("Criterio de desempate")
    preset_sel = st.selectbox("Regla", list(PRESETS.keys()), label_visibility="collapsed")
    if PRESETS[preset_sel] != st.session_state.CRITERIOS:
        st.session_state.CRITERIOS = PRESETS[preset_sel]
        if st.session_state.ESTADO:
            E = st.session_state.ESTADO
            cargar_estado(E["equipos"], E["jugados"], E["pendientes"])
            st.rerun()

    st.divider()

    # Estructura de clasificación
    st.subheader("Estructura de clasificación")
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.DIRECTO = st.number_input("Clasifican directos", min_value=1, max_value=10, value=st.session_state.DIRECTO)
    with col2:
        st.session_state.MEJORES_TERCEROS = st.number_input("Mejores 3ºs", min_value=0, max_value=20, value=st.session_state.MEJORES_TERCEROS,
                                                              help="0 = los terceros NO clasifican")
    st.session_state.CAMPEON = st.text_input("Nombre del 1º", value=st.session_state.CAMPEON,
                                              help='Ej: "campeón", "1º de zona", "ganador del grupo"')

    with st.expander("🎨 Zonas con nombre (para ligas)"):
        st.caption("Pinta la tabla por zonas. Una por línea: «hasta_puesto nombre». Ej.: «3 Libertadores».")
        _PZ = {"(sin zonas)": "",
               "Liga Argentina (tabla anual)": "3 Libertadores\n9 Sudamericana\n29 Permanece\n30 Descenso",
               "Clasificación simple": "4 Clasifica\n17 Permanece\n20 Descenso"}
        _pzsel = st.selectbox("Preset", list(_PZ.keys()), key="zpreset")
        if st.session_state.get("_zlast") != _pzsel:
            st.session_state.ZONAS_TXT = _PZ[_pzsel]
            st.session_state["_zlast"] = _pzsel
        _ztxt = st.text_area("Zonas", value=st.session_state.ZONAS_TXT, height=120, label_visibility="collapsed")
        st.session_state.ZONAS_TXT = _ztxt
        st.session_state.ZONAS = parse_zonas(_ztxt)
        if st.session_state.ZONAS:
            st.caption("Activas: " + " · ".join(f"≤{h} {n}" for h, n, _ in st.session_state.ZONAS))

    with st.expander("📉 Promedios (descenso a la argentina)"):
        st.caption("Pegá las temporadas **previas** de cada equipo: «Equipo, pts, pj» o «Equipo, pts1, pj1, pts2, pj2». "
                   "La temporada actual la toma sola de la tabla cargada. Los recién ascendidos no van (computan solo la actual).")
        _ptxt = st.text_area("Temporadas previas", value=st.session_state.get("PROM_TXT", ""), height=120,
                             placeholder="River, 85, 44\nBoca, 78, 44\nTigre, 41, 44", label_visibility="collapsed")
        st.session_state.PROM_TXT = _ptxt
        st.session_state.PROMEDIOS = parse_promedios(_ptxt)
        st.session_state.PROM_K = st.number_input("Descienden por promedio", 1, 5, int(st.session_state.get("PROM_K", 1)))
        if st.session_state.PROMEDIOS:
            st.caption(f"Cargadas previas de {len(st.session_state.PROMEDIOS)} equipos. Pedí «promedios» o «promedio de X» en el chat.")

    st.divider()

    # Cargar datos
    st.subheader("📥 Cargar datos")
    modo_carga = st.radio("Fuente", ["API football-data.org", "Pegar resultados", "Pegar tabla + fixture (ligas)", "Importar JSON/CSV (Apify u otra fuente)"], label_visibility="collapsed")

    texto_torneo = ""

    if modo_carga == "API football-data.org":
        token = st.text_input("API Key", value=_secret("FOOTBALL_DATA_TOKEN", ""), type="password",
                               placeholder="Tu token de football-data.org",
                               help="Cargala una vez en Secrets (FOOTBALL_DATA_TOKEN) y queda precargada.")
        comp  = st.text_input("Código torneo", value="WC",
                              help="Ej.: WC=Mundial, CL=Champions, PL=Premier, PD=LaLiga, SA=Serie A, "
                                   "BL1=Bundesliga, FL1=Ligue 1, BSA=Brasileirão, PPL=Portugal, "
                                   "DED=Eredivisie, ELC=Championship. Tocá «Ver torneos» para ver los tuyos.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🌐 Traer datos", use_container_width=True):
                if not token:
                    st.error("Pegá tu API key.")
                else:
                    try:
                        with st.spinner("Trayendo…"):
                            matches = traer_de_api(token, comp)
                        st.session_state.texto_torneo_cache = matches_a_texto(matches)
                        st.success("Datos cargados ✓")
                    except Exception as e:
                        st.error(f"Error: {e}")
        with col2:
            if st.button("Ver torneos", use_container_width=True):
                if token:
                    try:
                        st.session_state["lista_comps"] = listar_competiciones(token)
                    except Exception as e:
                        st.error(str(e))
        if "lista_comps" in st.session_state:
            for code, name in st.session_state["lista_comps"]:
                st.caption(f"`{code}` — {name}")
        texto_torneo = st.session_state.texto_torneo_cache

    elif modo_carga == "Pegar tabla + fixture (ligas)":
        if "liga_tabla_fetch" in st.session_state:
            st.session_state["liga_tabla_txt"] = st.session_state.pop("liga_tabla_fetch")
        st.caption("Pegá la **tabla** (una línea por equipo: «Equipo, Pts, PJ, DG»). Abajo, lo ideal es pegar el **fixture** que viene (líneas «River vs Boca») para captar los cruces entre rivales; si no, poné «faltan N fechas» (atajo, no ve los cruces).")
        with st.expander("🌐 Traer la tabla desde una URL (Wikipedia, gratis)"):
            url_tabla = st.text_input("URL de la página con la tabla", key="url_tabla",
                                      placeholder="https://es.wikipedia.org/wiki/Torneo_… (página del torneo)")
            if st.button("Leer tabla de la URL", use_container_width=True):
                txt_t, err_t = tabla_desde_url(url_tabla)
                if err_t:
                    st.error(err_t)
                else:
                    st.session_state["liga_tabla_fetch"] = txt_t
                    st.rerun()
            if st.button("Leer TODO: resultados + fixture (tabla cruzada) y cargar", use_container_width=True, type="primary"):
                jg2, pd2, err2, nota2 = partidos_desde_url(url_tabla)
                if err2:
                    st.error(err2)
                elif not jg2 and not pd2:
                    st.error("La matriz está vacía. Pegá tabla y fixture a mano.")
                else:
                    eqs2 = sorted({t for par in (jg2 + pd2) for t in (par[0], par[1])})
                    base2 = _stats(eqs2, jg2)
                    rest2 = liga_restantes(eqs2, pd2, None)
                    st.session_state.ESTADO = dict(modo="liga_tabla", equipos=eqs2, base=base2,
                                                   pendientes=pd2, rest=rest2, gleft=None,
                                                   jugados=jg2, esc=None, mg=0, solo_puntos=True)
                    st.success(f"Cargado desde la matriz: {len(jg2)} resultados y {len(pd2)} por jugar ({nota2}) ✓")
                    st.rerun()
        tabla_txt = st.text_area("Tabla de posiciones", height=170,
                                 placeholder="River Plate, 31, 14, +12\nBoca Juniors, 28, 14, +7\nRacing, 27, 14, +5\n...",
                                 key="liga_tabla_txt")
        fix_txt = st.text_area("Fechas que faltan (o fixture)", height=80,
                               placeholder="faltan 5 fechas\n— o pegá los partidos: River vs Boca …",
                               key="liga_fix_txt")
        if st.button("✅ Cargar liga (tabla)", use_container_width=True, type="primary"):
            base, pend, gleft = parse_tabla_fixture((tabla_txt or "") + "\n" + (fix_txt or ""))
            if len(base) >= 3:
                eqs = list(base.keys()); rest = liga_restantes(eqs, pend, gleft)
                st.session_state.ESTADO = dict(modo="liga_tabla", equipos=eqs, base=base,
                                               pendientes=pend, rest=rest, gleft=gleft,
                                               jugados=[], esc=None, mg=0, solo_puntos=True)
                st.rerun()
            else:
                st.error("No pude leer la tabla. Probá el formato «Equipo, Pts, PJ, DG» (una línea por equipo).")
        texto_torneo = ""

    elif modo_carga == "Importar JSON/CSV (Apify u otra fuente)":
        st.caption("Para ligas que no están en la API. Reconoce `homeTeam/awayTeam/homeScore/awayScore/status/league`: "
                   "los terminados van como resultados y los programados como fixture.")
        imp_fil = st.text_input("Filtrar por liga (texto que contenga)", key="imp_fil",
                                placeholder="ej.: liga profesional / argentina")
        solo_fix = False
        if st.session_state.ESTADO and st.session_state.ESTADO.get("modo") == "liga_tabla":
            solo_fix = st.toggle("Usar solo como fixture de la tabla ya cargada", value=False,
                                 help="Ideal: tabla pegada a mano + fixture automático. Empareja nombres aunque no coincidan exactos.")
        with st.expander("⚡ Traer directo de Apify", expanded=True):
            apify_tok = st.text_input("Apify token", value=_secret("APIFY_TOKEN", ""), type="password",
                                      help="Gratis en apify.com → Settings → API tokens. Cargalo una vez en Secrets (APIFY_TOKEN).")
            apify_act = st.text_input("Actor", value="crawlerbros/flashscore-scraper",
                                      help="También sirve extractify-labs/flashscore-extractor (filtra por fecha −7..+7) o cualquier actor que devuelva partidos.")
            apify_inp = st.text_area("Input del actor (JSON)", value='{"sport": "football", "liveOnly": false, "maxItems": 500}', height=70)
            if st.button("🌐 Traer de Apify e importar", use_container_width=True, type="primary"):
                if not apify_tok:
                    st.error("Pegá tu token de Apify (o cargalo en Secrets como APIFY_TOKEN).")
                else:
                    try:
                        import json as _json
                        with st.spinner("Corriendo el actor…"):
                            items = traer_de_apify(apify_tok, apify_act, apify_inp)
                        jg, pd_, ligas, err = importar_partidos_json(_json.dumps(items), imp_fil)
                        if err:
                            st.error(err)
                        elif _procesar_import(jg, pd_, ligas, imp_fil, solo_fix):
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
        imp_txt = st.text_area("…o pegá el JSON/CSV exportado", height=140, key="imp_txt",
                               placeholder='[{"homeTeam":"Lanus","awayTeam":"Banfield","homeScore":1,"awayScore":0,'
                                           '"status":"finished","league":"ARGENTINA: Liga Profesional"}, …]')
        if st.button("✅ Importar y cargar", use_container_width=True):
            jg, pd_, ligas, err = importar_partidos_json(imp_txt, imp_fil)
            if err:
                st.error(err)
            elif _procesar_import(jg, pd_, ligas, imp_fil, solo_fix):
                st.rerun()
        texto_torneo = ""

    else:
        texto_torneo = st.text_area(
            "Pegá los resultados",
            height=200,
            placeholder="Grupo A\nEspaña 0-0 Cabo Verde\nUruguay 1-1 Arabia Saudita\n...",
        )
        if texto_torneo.strip():
            st.session_state.texto_torneo_cache = texto_torneo

    grupos_disponibles = list(dividir_grupos(texto_torneo).keys()) if texto_torneo.strip() else []

    if grupos_disponibles:
        grupo_sel = st.selectbox("📂 Grupo a analizar", grupos_disponibles)
        if st.button("✅ Cargar grupo", use_container_width=True, type="primary"):
            texto_grupo = dividir_grupos(texto_torneo).get(grupo_sel, "")
            eq, jug, pen = parsear_resultados(texto_grupo)
            if len(eq) >= 3:
                cargar_estado(eq, jug, pen)
                st.rerun()
            else:
                st.error("No se detectaron suficientes equipos.")

    if st.session_state.ESTADO:
        E = st.session_state.ESTADO
        st.divider()
        if E.get("modo") == "liga_tabla":
            st.success(f"Liga cargada (tabla) · {len(E['equipos'])} equipos")
            falt = E.get("gleft")
            st.caption((f"Faltan {falt} fechas" if falt else f"{len(E['pendientes'])} partidos pendientes") + " · cuentas por puntos.")
        elif E.get("esc") is None:
            st.success(f"Liga cargada · {len(E['equipos'])} equipos · modo por puntos")
            st.caption(f"Pendientes: {len(E['pendientes'])} — son demasiados para enumerar marcador por marcador, así que voy por puntos.")
        else:
            st.success(f"Grupo cargado · {len(E['equipos'])} equipos · {len(E['esc']):,} escenarios")
            st.caption(f"Máx goles/equipo: {E['mg']} · Pendientes: {len(E['pendientes'])}")

# ─── MAIN TABS ───────────────────────────────────────────────────────────────────
if not st.session_state.ESTADO:
    st.info("👈 Cargá un grupo desde el panel lateral, o probá con el ejemplo del Mundial 2026:")
    if st.button("⚽ Usar Grupo H (España · Uruguay · Cabo Verde · Arabia Saudita)", type="primary"):
        cargar_estado(
            ["España", "Uruguay", "Cabo Verde", "Arabia Saudita"],
            [("España", "Cabo Verde", 0, 0), ("España", "Arabia Saudita", 4, 0),
             ("Uruguay", "Cabo Verde", 2, 2), ("Uruguay", "Arabia Saudita", 1, 1)],
            [("Uruguay", "España"), ("Cabo Verde", "Arabia Saudita")])
        st.rerun()
    st.stop()

E = st.session_state.ESTADO
equipos    = E["equipos"]
jugados    = E["jugados"]
pendientes = E["pendientes"]
esc        = E["esc"]

# ─── INTERFAZ DE CHAT ────────────────────────────────────────────────────────────
import unicodedata, json, re as _re

def _secret(k, default=""):
    try:
        return st.secrets.get(k, default)
    except Exception:
        return default

if "LLM_KEY"   not in st.session_state: st.session_state.LLM_KEY   = _secret("ANTHROPIC_API_KEY", "")
if "LLM_MODEL" not in st.session_state: st.session_state.LLM_MODEL = _secret("ANTHROPIC_MODEL", "claude-haiku-4-5")
if "LLM_ON"    not in st.session_state: st.session_state.LLM_ON    = bool(str(st.session_state.LLM_KEY).strip())


def _norm_txt(s):
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()


def detectar_equipo(q, equipos):
    qn = _norm_txt(q)
    pares = [(e, _norm_txt(e)) for e in equipos]
    full = [e for e, en in pares if en in qn]
    if full:
        return max(full, key=len)
    for e, en in pares:
        for w in en.split():
            if len(w) >= 4 and w in qn:
                return e
    return None

def detectar_equipos(q, equipos, k=2):
    qn = _norm_txt(q); found = []
    for e in sorted(equipos, key=lambda x: -len(x)):
        if _norm_txt(e) in qn and e not in found:
            found.append(e)
        if len(found) >= k:
            break
    return found

def _pos_pedida(qn):
    m = _re.search(r"\b([1-9])\s*[oº°]?\b", qn)
    if m:
        return int(m.group(1))
    for w, k in [("primer", 1), ("segundo", 2), ("tercer", 3), ("cuarto", 4), ("quinto", 5)]:
        if w in qn:
            return k
    return None

def _placa(spec, fname):
    return ("placa", _html_tabla(spec), _png_tabla(spec), fname)

def _placa_png(png, fname):
    return ("placa", None, png, fname)


# ─── NAVEGACIÓN ENTRE GRUPOS (si se cargó el torneo completo) ─────────────────────
def _tour_grupos():
    """Devuelve {label: (equipos, jugados, pendientes)} desde el texto del torneo."""
    txt = st.session_state.get("texto_torneo_cache", "")
    if not txt or not txt.strip():
        return {}
    out = {}
    for lab, sub in dividir_grupos(txt).items():
        try:
            eqs, jug, pen = parsear_resultados(sub)
        except Exception:
            continue
        if len(eqs) >= 3:
            out[lab] = (eqs, jug, pen)
    return out


def _buscar_grupo_de(team_q):
    for lab, (eqs, jug, pen) in _tour_grupos().items():
        t = detectar_equipo(team_q, eqs)
        if t:
            return lab, t, (eqs, jug, pen)
    return None, None, None


AYUDA_MD = """**Todo esto funciona escribiéndolo (no hace falta el asistente Claude).** Ejemplos:

**Qué necesita cada uno**
- *¿Qué necesita España?* · *¿Puede ser campeón Cabo Verde?* · *¿Qué necesita Arabia para no descender?*
- *¿Qué le conviene a Uruguay?* (su resultado + qué hinchar en los otros partidos)
- *¿De quién depende?* (si cada equipo depende de sí mismo o necesita ayuda) · *Si terminara hoy*

**Datos del grupo**
- *Tabla* · *Panorama* · *Probabilidades* · *Número mágico de España* · *Máximos* · *Asegurados*

**Buscar grupos** (con el torneo completo cargado)
- *¿En qué grupo está Brasil?* · *Equipos del grupo C* · *¿Qué grupos hay?*

**Placas visuales (se descargan como imagen)**
- *Grilla de España* — qué necesita, en cuadro de colores
- *Comparar España y Uruguay* — cara a cara
- *España puede salir 1º* — cuándo termina en ese puesto
- *Mapa del grupo* — mapa de calor de en qué puesto termina cada uno
- *¿Cómo viene España?* — explicación didáctica de sus chances, con medidor (placa)
- *Árbol de España* — flowchart si/entonces: gana → clasifica, empata → depende, etc. (placa)
- *Qué se juega cada equipo* — un renglón por equipo de todo el grupo, para placa o copete (placa)
- *Previa de la fecha* — qué define cada partido que falta y qué pasa con cada resultado (texto + placa)
- *Proyección* — cuántos puntos junta cada uno si mantiene su ritmo (tabla)
- *Ficha de España* — pts, ritmo, forma, racha, local/visitante, rivales que quedan y dificultad
- *Forma* / *Racha* — tabla de últimos 5 · *De local y de visitante* — rendimiento por condición
- *Calendario* — qué tan difícil es el fixture que le queda a cada uno
- *Mejores terceros* — el tablero de los 12 terceros con la línea de corte (necesita el torneo completo; placa)
- *Promedios* / *Promedio de X* — el descenso a la argentina, con piso, techo y análisis exacto (cargá las previas en el panel)
- *Barras de España* — distribución de en qué puesto puede terminar (gráfico)
- *Partido bisagra* — qué partido de los que faltan define más cosas
- *Tabla por zonas* — para ligas: pinta la tabla por Libertadores/Sudamericana/descenso (configurá las zonas en el panel)
- *Rival de Argentina en 16avos* — el cruce y los posibles rivales (cuadro oficial de FIFA)

**Simulador**
- *¿Qué pasa si…?* — panel interactivo: elegís los resultados que faltan y ves la tabla, quién clasifica y la previa en prosa.

**Entender el porqué**
- Después de casi cualquier respuesta, escribí *¿por qué?* y te desarmo la cuenta en criollo.
- Sirve sobre: *qué necesita X*, *ya clasificó / quedó afuera*, *número mágico*, *cómo viene X*, *partido bisagra*.

**Para la nota**
- *Contame el escenario de Uruguay* · *Relato del grupo* — texto listo para publicar

Podés encadenar sin repetir el equipo: *«¿qué necesita Uruguay?»* y después *«¿y qué le conviene?»*.
Si preguntás por un equipo de otro grupo, **cambio solo** a ese grupo."""

AYUDA_LIGA = """Esto es una **liga** (muchas fechas): trabajo **por puntos**. Comandos:

- **Tabla por zonas** — pinta Libertadores/Sudamericana/descenso (configurá las zonas en el panel)
- **¿Qué necesita River para Libertadores?** · **…para no descender** · **…para Sudamericana**
- **Número mágico de River** · **Máximos** (techo de cada uno) · **Asegurados top 4**
- **Si terminara hoy** · Después de cualquier respuesta, **¿por qué?** te desarma la cuenta
- **Chances de cada zona** (*probabilidades* o *¿cómo viene River?*) — simulación de miles de torneos, ideal a varias fechas del final
- **Proyección** — puntos finales si cada uno mantiene su ritmo
- **Comparar River y Boca** — cara a cara por puntos, techo y zona
- **Ficha de River** · **Calendario** (dificultad del fixture restante, con fixture pegado)
- **Promedios** · **Promedio de X** — descenso por promedios con temporadas previas (panel «📉 Promedios»)

Si cargaste por **tabla + fechas**, con eso me alcanza para todas estas cuentas (no necesito los resultados).
Configurá las zonas con nombre en «🎨 Zonas con nombre» del panel."""

BIENVENIDA = ("👋 Soy la **calculadora de escenarios**. Preguntame en lenguaje natural: "
              "*«¿qué necesita España?»*, *«¿en qué grupo está Brasil?»*, *«equipos del grupo C»*, "
              "*«tabla»*… Si no te acordás el grupo de un equipo, preguntá igual y lo busco. "
              "Escribí **ayuda** para ver todo.")


# ─── EJECUTOR DETERMINÍSTICO (las cuentas las hace el motor, nunca el LLM) ─────────
def _router_liga_tabla(acc, E):
    intent = acc.get("intent"); equipo = acc.get("equipo"); q = acc.get("q", "")
    base, rest = E["base"], E["rest"]; eqs = E["equipos"]
    z = st.session_state.get("ZONAS") or []
    if equipo and equipo not in eqs:
        equipo = detectar_equipo(equipo, eqs)
    if intent == "ayuda":
        return [("md", AYUDA_LIGA)]
    if intent in ("tabla", "hoy", "panorama"):
        out = []
        if z:
            out.append(_placa(spec_zonas_df(liga_tabla_df(base), z), "tabla_zonas.png"))
            out.append(("md", tabla_zonas_texto_df(liga_tabla_df(base), z)))
        else:
            out.append(("df", liga_tabla_df(base), "Tabla actual"))
        return out
    if intent == "zonas":
        if not z:
            return [("info", "Configurá las zonas en «🎨 Zonas con nombre» (panel) y volvé a preguntar.")]
        return [_placa(spec_zonas_df(liga_tabla_df(base), z), "tabla_zonas.png"),
                ("md", tabla_zonas_texto_df(liga_tabla_df(base), z))]
    if intent == "maximos":
        return [("df", liga_maxmin_df(base, rest), "Puntos máximos posibles")]
    if intent in ("probabilidades", "chances"):
        df = liga_probabilidades_df(base, rest, E["pendientes"], z)
        out = []
        if equipo:
            fila = df[df["Equipo"] == equipo]
            if len(fila):
                partes = [f"{c.replace(' %','')}: {fila[c].iloc[0]}%" for c in df.columns if c.endswith("%")]
                out.append(("md", f"**¿Cómo viene {equipo}?** (simulación) → " + " · ".join(partes)))
        out += [("df", df, "Chances por zona (cada 100 torneos simulados)"), ("md", NOTA_MC_LIGA)]
        return out
    if intent == "promedios":
        prevP = st.session_state.get("PROMEDIOS") or {}
        kk = int(st.session_state.get("PROM_K", 1))
        if equipo:
            return [("md", promedio_que_necesita_texto(equipo, base, rest, prevP, kk)),
                    ("df", promedios_df(base, rest, prevP), "Tabla de promedios (piso = perdiendo todo · techo = ganando todo)")]
        return [("df", promedios_df(base, rest, prevP), "Tabla de promedios (piso = perdiendo todo · techo = ganando todo)"),
                ("md", "_«Solo actual» = sin temporadas previas cargadas (recién ascendidos: es la regla). "
                       "Cargá las previas en el panel «📉 Promedios» y pedí «promedio de X» para el análisis._")]
    if intent == "terceros":
        return [("info", "El tablero de mejores terceros es para torneos por grupos (Mundial). En modo liga usá zonas, promedios o chances.")]
    if intent == "ficha":
        if not equipo:
            return [("warning", "¿De qué equipo? Ej.: «ficha de River».")]
        return [("md", ficha_liga_texto(equipo, base, rest, E["pendientes"], z))]
    if intent == "calendario":
        if not E["pendientes"]:
            return [("info", "Para la dificultad del calendario necesito el **fixture** (pegá los partidos «A vs B» en el panel).")]
        ppg = {e: (base[e]["pts"] / base[e].get("pj", 1)) if base[e].get("pj") else 0.0 for e in base}
        return [("df", dificultad_fixture_df(eqs, E["pendientes"], ppg, rest), "Dificultad del fixture restante"),
                ("md", "_«Dificultad» = promedio de puntos por partido de los rivales que le quedan a cada uno: cuanto más alto, más bravo el calendario._")]
    if intent in ("forma", "localia"):
        jugE = E.get("jugados") or []
        if not jugE:
            return [("info", "Para **forma** y **local/visitante** necesito los resultados partido a partido: "
                             "usá «Leer TODO» desde la URL de Wikipedia, importá el JSON del actor o pegá los resultados. "
                             "Con la tabla sola no puedo reconstruirlos.")]
        if intent == "localia":
            return [("df", local_visitante_df(eqs, jugE), "Rendimiento como local y como visitante")]
        out = []
        if equipo:
            ult, p5 = forma_equipo(equipo, jugE)
            out.append(("md", f"**{equipo}** viene {''.join(ult) or '—'} ({p5} pts en los últimos {len(ult)}) · racha: {racha_equipo(equipo, jugE)}."))
        out.append(("df", tabla_forma_df(eqs, jugE), "Tabla de forma (últimos 5: G/E/P)"))
        return out
    if intent == "proyeccion":
        return [("df", liga_proyeccion_df(base, rest), "Proyección a fin de torneo si cada uno mantiene su ritmo"),
                ("md", "_«Proyección (ritmo)» = puntos actuales + puntos por partido × partidos que restan. "
                       "Es la vara clásica para la nota; el techo es ganando todo._")]
    if intent == "comparar":
        e2 = acc.get("equipo2")
        if e2 and e2 not in eqs:
            e2 = detectar_equipo(e2, eqs)
        if not equipo or not e2:
            return [("warning", "Decime los dos equipos. Ej.: «comparar River y Boca».")]
        return [("df", liga_comparar_df(equipo, e2, base, rest, z), f"{equipo} vs {e2}")]
    if intent == "asegurados":
        nn = acc.get("n") or DIRECTO()
        return [("df", liga_aseg_df(base, rest, nn), f"Asegurados / sin chances (top {nn})")]
    if intent in ("duelos", "cruces"):
        return [("md", liga_duelos_texto(base, rest, E["pendientes"], z))]
    if intent in ("necesita", "numero_magico", "puesto_exacto", "conviene", "depende"):
        if not equipo:
            return [("warning", "Decime el equipo. Ej.: «qué necesita River para Libertadores».")]
        return [("md", liga_que_necesita_texto(equipo, base, rest, z, q, E["pendientes"])),
                ("df", liga_maxmin_df(base, rest), "Puntos máximos posibles")]
    if intent == "relato":
        if not equipo:
            return [("info", "En modo liga, contame el equipo y la zona. Ej.: «qué necesita River para Libertadores».")]
        return [("md", liga_que_necesita_texto(equipo, base, rest, z, q or "", E["pendientes"])),
                ("df", liga_maxmin_df(base, rest), "Puntos máximos posibles")]
    return [("info", "Cargaste una **liga por tabla**. Probá: «tabla por zonas», «qué necesita River para Libertadores», "
                     "«máximos», «asegurados top 4». (Para escenarios marcador-a-marcador, cargá un grupo por resultados.)")]


def _explicar_porque(E):
    u = st.session_state.get("ULTIMO") or {}
    equipo = u.get("equipo"); q = u.get("q", ""); intent = u.get("intent")
    if E.get("modo") == "liga_tabla":
        base, rest = E["base"], E["rest"]; z = st.session_state.get("ZONAS") or []
        if equipo:
            eq = detectar_equipo(equipo, E["equipos"]) or equipo
            r = _porque_liga(eq, base, rest, z, q)
            if r:
                return [("md", "🔍 **Por qué:** " + r)]
        return [("info", "Preguntá algo concreto (ej.: «qué necesita River para Libertadores») y después «¿por qué?».")]
    eqs, jug, pen, esc = E["equipos"], E["jugados"], E["pendientes"], E["esc"]
    if esc is None:
        if equipo:
            nn = 1 if u.get("objetivo") == "campeon" else (u.get("n") or DIRECTO())
            return [("md", "🔍 **Por qué:** " + _porque_numero_magico(detectar_equipo(equipo, eqs) or equipo, eqs, jug, pen, nn))]
        return [("info", "Preguntá «número mágico de X» o «qué necesita X» y después «¿por qué?».")]
    if intent == "bisagra":
        r = _porque_bisagra(eqs, jug, pen, esc)
        return [("md", "🔍 **Por qué:** " + r)] if r else [("info", "No quedan partidos para analizar.")]
    if equipo:
        eq = detectar_equipo(equipo, eqs) or equipo
        nn = u.get("n") or DIRECTO()
        return [("md", "🔍 **Por qué:** " + _porque_pasar(eq, eqs, jug, esc, pen, nn))]
    return [("info", "Preguntá algo concreto (ej.: «cómo viene España», «qué necesita España», «partido bisagra») y después «¿por qué?».")]


def ejecutar_accion(acc):
    intent = acc.get("intent")
    equipo = acc.get("equipo")
    objetivo = acc.get("objetivo")
    n = acc.get("n")
    E = st.session_state.ESTADO

    if intent == "porque":
        return _explicar_porque(E)

    # ── MODO LIGA POR TABLA (pegaste tabla + fechas) ──
    if E.get("modo") == "liga_tabla":
        return _router_liga_tabla(acc, E)

    eqs, jug, pen, esc = E["equipos"], E["jugados"], E["pendientes"], E["esc"]
    if equipo and equipo not in eqs:
        equipo = detectar_equipo(equipo, eqs)

    # ── TABLA POR ZONAS (sirve por puntos; ideal para ligas) ──
    if intent == "zonas":
        z = st.session_state.get("ZONAS") or []
        if not z:
            return [("info", "Todavía no configuraste zonas. Abrí «🎨 Zonas con nombre» en el panel y elegí un preset (ej.: Liga Argentina), o escribí las tuyas.")]
        return [_placa(spec_zonas(eqs, jug, z), "tabla_zonas.png"), ("md", tabla_zonas_texto(eqs, jug, z))]

    # ── CAMINO A 16AVOS / RIVALES (necesita el torneo completo cargado) ──
    if intent == "camino":
        grupos = _tour_grupos()
        if len(grupos) < 2:
            return [("info", "Para los cruces de 16avos necesito el torneo completo cargado (todos los grupos), por API o pegando todo.")]
        tt = acc.get("equipo") or equipo
        if not tt or not any(tt in g[0] for g in grupos.values()):
            tt = "Argentina" if any("Argentina" in g[0] for g in grupos.values()) else (_buscar_grupo_de(acc.get("equipo") or "")[1])
        if not tt:
            return [("warning", "¿De qué equipo querés el cruce? Ej.: «rival de Argentina en 16avos».")]
        spec = spec_camino(tt, grupos)
        if not spec:
            return [("warning", f"No encuentro a {tt} en los grupos cargados.")]
        return [_placa(spec, f"camino_{tt}.png"), ("md", camino_texto(tt, grupos))]

    if intent == "ficha":
        if not equipo:
            return [("warning", "¿De qué equipo? Ej.: «ficha de España».")]
        return [("md", ficha_equipo_texto(equipo, eqs, jug, pen))]
    if intent == "forma":
        out = []
        if equipo:
            ult, p5 = forma_equipo(equipo, jug)
            out.append(("md", f"**{equipo}** viene {''.join(ult) or '—'} ({p5} pts en los últimos {len(ult)}) · racha: {racha_equipo(equipo, jug)}."))
        out.append(("df", tabla_forma_df(eqs, jug), "Tabla de forma (últimos 5: G/E/P)"))
        return out
    if intent == "localia":
        return [("df", local_visitante_df(eqs, jug), "Rendimiento como local y como visitante")]
    if intent == "calendario":
        if not pen:
            return [("info", "No quedan partidos por jugar.")]
        ovx = _stats(eqs, jug); ppg = {e: (ovx[e]["pts"] / ovx[e]["pj"]) if ovx[e]["pj"] else 0.0 for e in eqs}
        return [("df", dificultad_fixture_df(eqs, pen, ppg), "Dificultad del fixture restante"),
                ("md", "_«Dificultad» = promedio de puntos por partido de los rivales que quedan: cuanto más alto, más bravo._")]

    if intent == "terceros":
        G = _tour_grupos()
        if len(G) < 2:
            return [("info", "Para el tablero de mejores terceros cargá el **torneo completo** "
                             "(API football-data o pegá todos los grupos juntos).")]
        png = placa_terceros_png(G)
        out = [("md", terceros_texto(G))]
        if png:
            out.insert(0, _placa_png(png, "mejores_terceros.png"))
        return out
    if intent == "promedios":
        ovx = _stats(eqs, jug); restx = _restantes(eqs, pen)
        basex = {e: {"pts": ovx[e]["pts"], "pj": ovx[e]["pj"], "dg": ovx[e]["dg"]} for e in eqs}
        prev = st.session_state.get("PROMEDIOS") or {}
        kk = int(st.session_state.get("PROM_K", 1))
        if equipo:
            return [("md", promedio_que_necesita_texto(equipo, basex, restx, prev, kk)),
                    ("df", promedios_df(basex, restx, prev), "Tabla de promedios (piso = perdiendo todo · techo = ganando todo)")]
        return [("df", promedios_df(basex, restx, prev), "Tabla de promedios (piso = perdiendo todo · techo = ganando todo)"),
                ("md", "_«Solo actual» = sin temporadas previas cargadas (recién ascendidos: es la regla). "
                       "Cargá las previas en el panel «📉 Promedios» y pedí «promedio de X» para el análisis._")]

    # ── MODO LIGA (por puntos): cuando hay demasiados partidos para enumerar ──
    if esc is None:
        if intent == "ayuda":
            return [("md", AYUDA_LIGA)]
        if intent == "tabla":
            return [("df", tabla(eqs, jug), "Tabla actual"), ("md", si_terminara_hoy_texto(eqs, jug, pen))]
        if intent in ("hoy", "panorama"):
            return [("md", si_terminara_hoy_texto(eqs, jug, pen)), ("df", tabla(eqs, jug), "Tabla actual")]
        if intent == "maximos":
            return [("df", maximos_minimos(eqs, jug, pen), "Puntos máximos posibles")]
        if intent == "asegurados":
            nn = n or DIRECTO()
            return [("df", clasificado_eliminado(eqs, jug, pen, nn), f"Asegurados / sin chances (top {nn})")]
        if intent == "probabilidades":
            return [("md", "Estimación por simulación (Poisson, 8.000 sorteos) con **fuerza estimada** por el rendimiento de cada equipo."),
                    ("df", probabilidades(eqs, jug, pen, fuerza=fuerza_desde_stats(eqs, jug)), "Probabilidades")]
        if intent == "chances":
            if not equipo:
                return [("warning", "¿De qué equipo? Ej.: «¿cómo viene River?».")]
            pct, dfp = chances_mc(equipo, eqs, jug, pen)
            return [_placa_png(placa_chances_mc_png(equipo, pct), f"chances_{equipo}.png"),
                    ("md", f"**¿Cómo viene {equipo}?** Clasifica en **{round(pct)} de cada 100 torneos simulados** "
                           f"(fuerza estimada por su rendimiento). _Como hay muchas fechas por delante, esto es simulación, no cuenta exacta._"),
                    ("df", dfp, "Probabilidades (simulación)")]
        if intent == "proyeccion":
            ov = _stats(eqs, jug); restx = _restantes(eqs, pen)
            basex = {e: {"pts": ov[e]["pts"], "pj": ov[e]["pj"], "dg": ov[e]["dg"]} for e in eqs}
            return [("df", liga_proyeccion_df(basex, restx), "Proyección si cada uno mantiene su ritmo"),
                    ("md", "_Proyección = puntos actuales + puntos por partido × partidos restantes._")]
        if intent in ("necesita", "numero_magico", "depende", "conviene", "visual", "puesto_exacto"):
            if not equipo:
                return [("warning", "Decime el equipo. Ej.: «número mágico de River» o «qué necesita River».")]
            nn = 1 if objetivo == "campeon" else (n or DIRECTO())
            return [("md", numero_magico_texto(equipo, eqs, jug, pen, nn)),
                    ("df", maximos_minimos(eqs, jug, pen), "Puntos máximos posibles")]
        return [("info", "Es una **liga** con muchas fechas, así que trabajo por puntos. Probá: "
                         "**tabla**, **si terminara hoy**, **número mágico de X**, **máximos**, "
                         "**asegurados** o **probabilidades**.")]

    if intent == "ayuda":
        return [("md", AYUDA_MD)]
    if intent == "tabla":
        return [("df", tabla(eqs, jug), "Tabla actual"),
                ("info", resumen_grupo_texto(eqs, jug, esc, pen))]
    if intent == "panorama":
        return [("info", resumen_grupo_texto(eqs, jug, esc, pen)),
                ("df", panorama(eqs, jug, esc), "Panorama de clasificación")]
    if intent == "probabilidades":
        return [("md", "Probabilidades estimadas por simulación (Poisson, ~8.000 sorteos) con **fuerza estimada** por el rendimiento de cada equipo. Es una estimación, no la cuenta exacta."),
                ("df", probabilidades(eqs, jug, pen, fuerza=fuerza_desde_stats(eqs, jug)), "Probabilidades")]
    if intent == "proyeccion":
        ov = _stats(eqs, jug); restx = _restantes(eqs, pen)
        basex = {e: {"pts": ov[e]["pts"], "pj": ov[e]["pj"], "dg": ov[e]["dg"]} for e in eqs}
        return [("df", liga_proyeccion_df(basex, restx), "Proyección si cada uno mantiene su ritmo"),
                ("md", "_Proyección = puntos actuales + puntos por partido × partidos restantes._")]
    if intent == "maximos":
        return [("df", maximos_minimos(eqs, jug, pen), "Puntos máximos posibles")]
    if intent == "hoy":
        return [("md", si_terminara_hoy_texto(eqs, jug, pen)),
                ("df", tabla(eqs, jug), "Tabla actual")]
    if intent == "depende":
        if equipo:
            cat, msg = en_sus_manos(equipo, esc, pen)
            icon = {"manos": "🟢", "ayuda": "🟡", "ya": "✅", "out": "🔴"}.get(cat, "•")
            return [("md", f"### ¿De qué depende {equipo}?"), ("md", f"{icon} **{equipo}** — {msg}"),
                    ("df", tabla(eqs, jug), "Tabla actual")]
        return [("md", en_sus_manos_texto(eqs, jug, esc, pen)),
                ("df", tabla(eqs, jug), "Tabla actual")]
    if intent == "relato":
        if equipo:
            return [("md", f"### {equipo} · el escenario"),
                    ("md", relato_equipo_texto(equipo, eqs, jug, esc, pen))]
        return [("md", "### El grupo · el escenario"),
                ("md", relato_grupo_texto(eqs, jug, esc, pen))]
    if intent == "visual":
        if not equipo:
            return [("warning", "¿De qué equipo querés la grilla? Probá «grilla de España».")]
        spec = spec_necesita(equipo, esc, pen)
        if not spec:
            return [("info", f"A {equipo} le queda más de un partido, así que la grilla sería enorme. Va el detalle en texto:"),
                    ("md", que_necesita_completo_texto(equipo, esc, pen))]
        return [_placa(spec, f"necesita_{equipo}.png")]
    if intent == "mapa":
        return [_placa(spec_mapa(eqs, esc), "mapa_grupo.png")]
    if intent == "bisagra":
        out = [("md", "### Partidos que más definen"), ("md", partido_bisagra_texto(eqs, jug, pen, esc))]
        png = placa_bisagra_png(eqs, jug, pen, esc)
        if png:
            out.append(_placa_png(png, "partidos_bisagra.png"))
        return out
    if intent == "barras":
        if not equipo:
            return [("warning", "¿De qué equipo? Ej.: «barras de España».")]
        return [_placa_png(barras_puesto_png(equipo, esc), f"barras_{equipo}.png")]
    if intent == "chances":
        if not equipo:
            return [("warning", "¿De qué equipo querés ver las chances? Ej.: «¿cómo viene España?».")]
        return [_placa_png(placa_chances_png(equipo, eqs, jug, esc, pen), f"chances_{equipo}.png"),
                ("md", chances_texto(equipo, eqs, jug, esc, pen))]
    if intent == "arbol":
        if not equipo:
            return [("warning", "¿De qué equipo querés el árbol? Ej.: «árbol de España».")]
        png = placa_arbol_png(equipo, eqs, jug, esc, pen)
        if not png:
            return [("info", f"{equipo} tiene demasiados partidos pendientes para un árbol claro; probá «qué necesita {equipo}».")]
        return [_placa_png(png, f"arbol_{equipo}.png"),
                ("md", f"Árbol de decisión de **{equipo}** según su resultado. Para el detalle escrito, pedí «qué necesita {equipo}».")]
    if intent == "previa":
        lab = ""
        for L2, (e2, _, _) in _tour_grupos().items():
            if set(e2) == set(eqs):
                lab = L2; break
        out = [("md", previa_fecha_texto(eqs, jug, esc, pen))]
        png = placa_previa_fecha_png(eqs, jug, esc, pen, lab)
        if png:
            out.append(_placa_png(png, "previa_fecha.png"))
        return out
    if intent == "juega":
        lab = ""
        for L2, (e2, _, _) in _tour_grupos().items():
            if set(e2) == set(eqs):
                lab = L2; break
        return [_placa_png(placa_que_se_juega_png(eqs, jug, esc, pen, lab), "que_se_juega.png"),
                ("md", que_se_juega_texto(eqs, jug, esc, pen))]
    if intent == "simulador":
        return [("info", "Abrí el panel **🎮 Simulador: ¿qué pasa si…?** (arriba de las sugerencias). "
                         "Elegí el resultado de cada partido que falta y te muestro la tabla resultante, quién clasifica y la previa en prosa.")]
    if intent == "comparar":
        e2 = acc.get("equipo2")
        if not (equipo and e2):
            return [("warning", "Decime los dos equipos. Ej.: «comparar España y Uruguay».")]
        if e2 not in eqs:
            e2 = detectar_equipo(e2, eqs)
        if not e2 or e2 == equipo:
            return [("warning", "Necesito dos equipos distintos del mismo grupo para comparar.")]
        return [_placa(spec_comparar(equipo, e2, eqs, jug, esc, pen), f"comparar_{equipo}_{e2}.png")]
    if intent == "puesto":
        if not equipo:
            return [("warning", "¿De qué equipo? Ej.: «España puede salir 1º».")]
        puesto = n or 1
        spec = spec_puesto(equipo, esc, pen, puesto)
        if not spec:
            return [("info", f"A {equipo} le queda más de un partido; la grilla sería enorme. Va el detalle en texto:"),
                    ("md", resultados_para_puesto_texto(equipo, esc, pen, ("exacto", puesto)))]
        return [_placa(spec, f"{equipo}_puesto_{puesto}.png")]
    if intent == "asegurados":
        nn = n or DIRECTO()
        return [("df", clasificado_eliminado(eqs, jug, pen, nn), f"Asegurados / sin chances (top {nn})")]
    if intent == "numero_magico":
        if not equipo:
            return [("warning", "¿De qué equipo? Probá: «número mágico de España».")]
        nn = 1 if objetivo == "campeon" else (n or DIRECTO())
        return [("md", numero_magico_texto(equipo, eqs, jug, pen, nn))]

    if not equipo:
        return [("md", "No identifiqué a qué equipo te referís. " + AYUDA_MD)]

    team_pend = sum(1 for p in pen if equipo in p)
    muchos = team_pend >= 2

    if intent == "conviene":
        out = [("md", f"### Qué le conviene a {equipo}"), ("md", mejor_resultado_texto(equipo, esc, pen))]
        co = conviene_otros_texto(equipo, esc, pen)
        if co:
            out.append(("md", co))
        ideal = combo_ideal_texto(equipo, esc, pen)
        if ideal:
            out.append(("md", ideal))
        out.append(("df", tabla(eqs, jug), "Tabla actual"))
        return out

    if intent == "puesto_exacto" and n:
        return [("md", f"### {equipo}: terminar exactamente {n}º"),
                ("md", resultados_para_puesto_texto(equipo, esc, pen, ("exacto", n))),
                ("df", tabla(eqs, jug), "Tabla actual")]

    # intent == "necesita"
    if objetivo == "campeon":
        obj, nn = "campeon", 1
    elif objetivo == "champions":
        obj, nn = "top", 4
    elif objetivo == "descenso":
        obj, nn = "descenso", (n or 1)
    elif objetivo == "tercero":
        obj, nn = "tercero", 3
    else:
        obj, nn = "top", (n or DIRECTO())
    es_default = (obj == "top" and nn == DIRECTO())

    blocks = [("md", f"### ¿Qué necesita {equipo}?")]
    if obj == "tercero":
        if MEJORES_TERCEROS() > 0:
            blocks.append(("md", apartado_terceros_texto(equipo, esc, pen)))
        else:
            blocks.append(("info", "En este torneo los terceros no clasifican (Mejores 3ºs = 0 en el panel)."))
    elif muchos:
        blocks.append(("info", f"A {equipo} le quedan {team_pend} partidos: con tantos por jugar el detalle "
                               f"gol por gol es enorme, así que va el resumen por puntos."))
        blocks.append(("md", necesita_por_resultados_texto(equipo, eqs, jug, pen, nn)))
    else:
        s = situacion(equipo, esc)
        if es_default and s["ya_directo"]:
            blocks.append(("success", f"🟢 {equipo} ya clasificó directo (siempre entre los {DIRECTO()} primeros)."))
        elif es_default and s["eliminado"]:
            blocks.append(("error", f"🔴 {equipo} no llega a zona de clasificación en ningún escenario."))
        else:
            usar_unificado = es_default and MEJORES_TERCEROS() > 0 and s["puede_tercero"] and not s["ya_directo"]
            if usar_unificado:
                blocks.append(("md", que_necesita_completo_texto(equipo, esc, pen)))
                n3, T = s["ntercero"], s["total"]
                blocks.append(("info",
                    f"«3º · depende de otros grupos»: quedar tercero clasifica solo si {equipo} entra "
                    f"entre los {MEJORES_TERCEROS()} mejores terceros del torneo (se compara con los terceros "
                    f"de los otros grupos). {equipo} termina 3º en {n3}/{T} escenarios."))
                # El árbol ya muestra cuándo puede salir 1º (rango «1º-2º»), así que no repetimos el bloque de campeón.
            else:
                blocks.append(("md", que_necesita_texto(equipo, esc, pen, obj, n=nn)))
                if es_default and s["puede_1"] and not s["ya_1"]:
                    blocks += [("md", "---"), ("md", que_necesita_texto(equipo, esc, pen, "campeon"))]
    blocks.append(("df", tabla(eqs, jug), "Tabla actual (para ubicarse)"))
    return blocks


# ─── BLOQUES DE NAVEGACIÓN ────────────────────────────────────────────────────────
def _bloques_listar_grupos():
    gs = _tour_grupos()
    if len(gs) <= 1:
        return [("info", "Tenés cargado un solo grupo. Para tener todos, pegá o importá el torneo "
                         "completo desde el panel lateral (API o pegar texto).")]
    lineas = ["**Grupos cargados:**"]
    for lab, (eqs, _, _) in gs.items():
        lineas.append(f"- **Grupo {lab}**: " + ", ".join(eqs))
    return [("md", "\n".join(lineas))]


def _bloques_ver_grupo(lab):
    gs = _tour_grupos()
    lab = _norm_txt(lab or "").replace("grupo", "").strip().upper()
    if lab not in gs:
        disp = ", ".join(gs) if gs else "—"
        return [("warning", f"No encuentro el Grupo {lab}. Disponibles: {disp}. "
                            "(Si falta, cargá el torneo completo en el panel lateral.)")]
    eqs, jug, pen = gs[lab]
    cargar_estado(eqs, jug, pen)
    return [("success", f"Cargué el **Grupo {lab}**: {', '.join(eqs)}."),
            ("df", tabla(eqs, jug), f"Grupo {lab} — tabla actual"),
            ("info", resumen_grupo_texto(eqs, jug, st.session_state.ESTADO["esc"], pen))]


def _bloques_buscar_equipo(team_q):
    lab, team, datos = _buscar_grupo_de(team_q)
    if not lab:
        gs = _tour_grupos()
        if len(gs) <= 1:
            return [("warning", f"Solo tengo un grupo cargado, así que no puedo buscar en otros. "
                                "Cargá el torneo completo (API o pegar) desde el panel lateral.")]
        return [("warning", f"No encontré ese equipo en los grupos cargados. ¿Está bien escrito?")]
    eqs, jug, pen = datos
    cargar_estado(eqs, jug, pen)
    comp = [e for e in eqs if e != team]
    return [("success", f"**{team}** está en el **Grupo {lab}**, junto a {', '.join(comp)}."),
            ("info", f"Cambié a ese grupo: ya podés preguntar, por ejemplo «¿qué necesita {team}?»."),
            ("df", tabla(eqs, jug), f"Grupo {lab} — tabla actual")]


# ─── ROUTER POR PALABRAS CLAVE (fallback, sin LLM) ────────────────────────────────
def _parse_kw(q):
    qn = _norm_txt(q)
    eqs = st.session_state.ESTADO["equipos"]
    team = detectar_equipo(q, eqs)
    has = lambda *ws: any(w in qn for w in ws)
    nw = len(qn.split())
    if (has("por que", "porque", "porqué") and nw <= 3) or has("explicame", "explicalo", "explica eso", "fundamento", "de donde sale", "de donde sacas", "como llegaste", "como sacas eso"):
        return {"intent": "porque"}
    m = _re.search(r"top\s*(\d+)|primeros?\s*(\d+)|(\d+)\s*primeros|puesto\s*(\d+)|(\d+)\s*[oº]", qn)
    n_det = int(next(g for g in m.groups() if g)) if m else None
    mg = _re.search(r"grupo\s+([a-l])\b", qn)

    if has("ayuda", "help", "que puedo", "como funciona"):
        return {"intent": "ayuda"}
    if has("relato", "contame", "para la nota", "escribime", "escribi ", "narra", "narrá", "parrafo", "párrafo", "escenario escrito", "resumen escrito", "resumime", "redacta"):
        return {"intent": "relato", "equipo": team}
    if has("arbol", "árbol", "flowchart", "diagrama de decision", "arbol de decision", "si entonces", "diagrama si"):
        return {"intent": "arbol", "equipo": team}
    if has("previa", "previa de la fecha", "que se define en cada", "que define cada partido", "preview", "que define cada uno de los partidos"):
        return {"intent": "previa"}
    if has("que se juega", "qué se juega", "se juega cada", "en una frase", "que necesita cada", "resumen en frases", "que esta en juego"):
        return {"intent": "juega"}
    if has("simulador", "que pasa si", "simular", "y si gana", "y si pierde", "y si empata", "que pasaria si"):
        return {"intent": "simulador"}
    if has("cruces directos", "cruce directo", "duelos directos", "duelo directo", "rivales directos", "mano a mano", "partidos entre", "seis puntos", "finales entre"):
        return {"intent": "duelos"}
    if has("zonas", "por zona", "tabla por zona", "tabla con zona", "mostrar zonas", "ver zonas"):
        return {"intent": "zonas"}
    if has("16avos", "dieciseisavos", "cruce", "rival", "posible rival", "posibles rivales", "camino", "contra quien", "a quien enfrenta", "con quien le toca", "con quien juega"):
        _allt = [e for (e2, _, _) in _tour_grupos().values() for e in e2] or eqs
        tcam = detectar_equipo(q, _allt) or ("Argentina" if "Argentina" in _allt else None)
        return {"intent": "camino", "equipo": tcam}
    if has("visual", "grilla", "matriz", "cuadro de escenarios", "mapa de escenarios", "tabla de escenarios", "grafic", "placa"):
        return {"intent": "visual", "equipo": team}
    if has("mejores terceros", "tabla de terceros", "tablero de terceros", "los terceros", "terceros clasificados") or "terceros" in qn.split():
        return {"intent": "terceros"}
    if has("promedios", "promedio de", "el promedio", "descenso por promedio", "desciende por promedio"):
        return {"intent": "promedios", "equipo": team}
    if has("ficha de", "ficha del", "stats de", "estadisticas de", "estadisticas del", "numeros de", "los numeros de"):
        return {"intent": "ficha", "equipo": team}
    toks = set(qn.split())
    if ("forma" in toks and "informe" not in qn) or has("ultimos 5", "ultimos cinco", "racha", "rachas", "tabla de forma"):
        return {"intent": "forma", "equipo": team}
    if has("calendario", "dificultad", "fixture dificil", "fixture mas dificil", "fixture restante", "rivales que quedan", "que rivales le quedan", "fixture que queda"):
        return {"intent": "calendario", "equipo": team}
    if has("de local", "de visitante", "localia", "local y visitante", "como local", "como visitante", "rendimiento local"):
        return {"intent": "localia", "equipo": team}
    if has("proyeccion", "proyección", "proyectado", "ritmo", "a este paso", "promedio de puntos", "puntos por partido"):
        return {"intent": "proyeccion"}
    if has("como viene", "como esta", "como llega", "chances", "que chance", "esta complicado", "esta bien parado", "esta para clasificar", "esta adentro", "esta afuera", "termometro"):
        return {"intent": "chances", "equipo": team}
    if has("bisagra", "partido clave", "partido decisivo", "partido mas importante", "que partido define", "que se define", "mas define", "partido mas decisivo"):
        return {"intent": "bisagra"}
    if has("barras", "en barras", "distribucion", "grafico de barras", "chances por puesto", "reparto por puesto"):
        return {"intent": "barras", "equipo": team}
    if has("mapa", "calor", "heatmap", "reparto de puesto", "como se reparten", "donde termina cada"):
        return {"intent": "mapa"}
    if has("comparar", "compara", "versus", " vs ", "vs.", "mano a mano", "frente a", "enfrenta", "contra "):
        dos = detectar_equipos(q, eqs, 2)
        if len(dos) == 2:
            return {"intent": "comparar", "equipo": dos[0], "equipo2": dos[1]}
    _posq = _pos_pedida(qn)
    if _posq and has("puede salir", "puede ser", "puede terminar", "puede quedar", "sale ", "termina", "terminar", "queda ", "salir") and not has("necesita", "conviene"):
        return {"intent": "puesto", "equipo": team, "n": _posq}
    # navegación de grupos
    if has("en que grupo", "en cual grupo", "donde juega", "donde esta", "de que grupo", "grupo de", "que grupo es"):
        return {"intent": "buscar_equipo", "equipo": q}
    if has("que grupos", "cuales grupos", "lista de grupos", "todos los grupos", "ver grupos") or qn.strip() == "grupos":
        return {"intent": "listar_grupos"}
    if mg and has("grupo"):
        return {"intent": "ver_grupo", "grupo": mg.group(1)}

    if has("termina hoy", "terminara hoy", "si terminara", "quedaria hoy", "como quedaria", "quien pasa hoy", "clasifica hoy", "tabla de hoy", "fase hoy"):
        return {"intent": "hoy"}
    if has("de quien depende", "depende de si", "en sus manos", "depende de el mismo", "depende de ella", "lo tiene en sus manos", "quien depende"):
        return {"intent": "depende", "equipo": team}
    if has("tabla", "posicion") and not has("conviene", "necesita"):
        return {"intent": "tabla"}
    if has("panorama", "pantallazo", "como esta el grupo", "como viene") or (has("resumen") and not team):
        return {"intent": "panorama"}
    if has("probabilidad", "chance", "porcentaje"):
        return {"intent": "probabilidades"}
    if has("maximo", "puntos posibles", "techo"):
        return {"intent": "maximos"}
    if has("asegurad", "eliminad", "quien esta adentro", "clasificado"):
        return {"intent": "asegurados", "n": n_det}
    if has("numero magico", "magico", "asegurar"):
        return {"intent": "numero_magico", "equipo": team, "objetivo": "campeon" if has("campeon", "primero") else None, "n": n_det}
    if has("conviene", "le sirve", "hinchar", "para quien", "le rinde"):
        return {"intent": "conviene", "equipo": team}
    if has("exacto", "exactamente") and n_det:
        return {"intent": "puesto_exacto", "equipo": team, "n": n_det}
    if has("campeon", "salir primero", "ganar el grupo", "ganar la zona"):
        return {"intent": "necesita", "equipo": team, "objetivo": "campeon"}
    if has("champions"):
        return {"intent": "necesita", "equipo": team, "objetivo": "champions"}
    if has("descenso", "descender", "salvar", "no bajar"):
        return {"intent": "necesita", "equipo": team, "objetivo": "descenso", "n": n_det or 1}
    if has("tercero", "mejor tercero"):
        return {"intent": "necesita", "equipo": team, "objetivo": "tercero"}
    return {"intent": "necesita", "equipo": team, "objetivo": "clasificar", "n": n_det}


# ─── ROUTER CON LLM (solo interpreta; las cuentas siguen en Python) ────────────────
def _llm_parse(q):
    gs = _tour_grupos()
    if gs:
        contexto = "Grupos y equipos del torneo:\n" + "\n".join(f"- Grupo {lab}: {', '.join(d[0])}" for lab, d in gs.items())
    else:
        contexto = "Equipos del grupo cargado: " + ", ".join(st.session_state.ESTADO["equipos"])
    sistema = (
        "Sos un router de intención para una calculadora de escenarios de fútbol.\n" + contexto + "\n\n"
        "Respondé EXCLUSIVAMENTE un objeto JSON (sin texto extra, sin ```), con estas claves:\n"
        '- "intent": uno de [necesita, conviene, tabla, panorama, probabilidades, numero_magico, '
        'asegurados, maximos, puesto_exacto, buscar_equipo, ver_grupo, listar_grupos, depende, hoy, relato, '
        'visual, comparar, puesto, mapa, camino, bisagra, barras, zonas, chances, relato, duelos, porque, simulador, arbol, juega, previa, proyeccion, ficha, forma, calendario, localia, terceros, promedios, ayuda]\n'
        '- "equipo": nombre EXACTO de un equipo (de cualquier grupo) o null\n'
        '- "equipo2": segundo equipo (solo para comparar) o null\n'
        '- "grupo": letra del grupo (para ver_grupo) o null\n'
        '- "objetivo": solo si intent=necesita: [clasificar, campeon, champions, descenso, tercero]; default clasificar\n'
        '- "n": entero o null (top N, descenso N, o el puesto para intent=puesto/puesto_exacto)\n'
        '- "intro": una frase breve en español rioplatense que presente la respuesta, SIN dar números ni resultados.\n'
        "Pistas: 'en qué grupo está X'/'dónde juega X' => buscar_equipo (equipo=X). "
        "'equipos del grupo C'/'grupo C' => ver_grupo (grupo='C'). 'qué grupos hay' => listar_grupos. "
        "'de quién depende X'/'lo tiene en sus manos' => depende. 'si terminara hoy'/'quién pasa hoy' => hoy. "
        "'contame/escribime/relato/para la nota' => relato (equipo si lo nombran, si no el grupo). "
        "'grilla/visual/matriz' => visual (equipo). 'comparar X y Z'/'X vs Z' => comparar (equipo=X, equipo2=Z). "
        "'X puede salir/terminar Nº' => puesto (equipo=X, n=N). 'mapa/mapa de calor/dónde termina cada uno' => mapa. "
        "'mejores terceros'/'tablero de terceros' => terceros. 'promedios'/'promedio de X'/'desciende por promedio' => promedios (equipo=X si lo nombra). 'ficha de X'/'stats de X' => ficha. 'forma'/'racha'/'últimos 5' => forma. 'calendario'/'dificultad del fixture'/'rivales que quedan' => calendario. 'de local'/'de visitante' => localia. 'proyección'/'ritmo'/'a este paso cuánto suma' => proyeccion. 'por qué'/'explicame'/'de dónde sale eso' (a secas, sin equipo) => porque (explica la última respuesta). 'cómo viene X'/'qué chances tiene X'/'está para clasificar X'/'termómetro de X' => chances (equipo=X). 'contame el escenario de X'/'relato de X' => relato (equipo=X); 'relato del grupo' => relato sin equipo. 'rival de X'/'cruce de X en 16avos'/'camino de X'/'posibles rivales' => camino (equipo=X; si no nombran equipo y juega Argentina, equipo=Argentina). "
        "'campeón'/'ganar el grupo' => objetivo campeon. 'no descender' => descenso."
    )
    body = {"model": st.session_state.LLM_MODEL, "max_tokens": 400,
            "system": sistema, "messages": [{"role": "user", "content": q}]}
    r = requests.post("https://api.anthropic.com/v1/messages",
                      headers={"x-api-key": st.session_state.LLM_KEY,
                               "anthropic-version": "2023-06-01",
                               "content-type": "application/json"},
                      json=body, timeout=30)
    r.raise_for_status()
    data = r.json()
    txt = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text").strip()
    obj = json.loads(txt[txt.find("{"): txt.rfind("}") + 1])
    return obj, obj.get("intro")


def responder(q):
    usar_llm = st.session_state.LLM_ON and str(st.session_state.LLM_KEY).strip()
    intro = None
    err_note = None
    if usar_llm:
        try:
            acc, intro = _llm_parse(q)
            st.session_state["LLM_ERROR"] = ""
        except Exception as e:
            acc = _parse_kw(q)
            st.session_state["LLM_ERROR"] = str(e)[:200]
            err_note = ("info", f"⚠️ El asistente Claude no respondió ({str(e)[:90]}…). Te respondo igual por palabras clave. "
                                "Revisá la API key y el modelo en el panel; o desactivalo (todo funciona por palabras clave: escribí «ayuda»).")
    else:
        acc = _parse_kw(q)

    pre = [("md", f"_{intro}_")] if intro else []
    if err_note:
        pre = [err_note] + pre
    acc["q"] = q
    intent = acc.get("intent")

    if intent == "listar_grupos":
        return pre + _bloques_listar_grupos()
    if intent == "ver_grupo":
        return pre + _bloques_ver_grupo(acc.get("grupo"))
    if intent == "buscar_equipo":
        return pre + _bloques_buscar_equipo(acc.get("equipo") or q)

    # Cambio automático de grupo si el equipo no está en el grupo cargado
    cur = st.session_state.ESTADO["equipos"]
    team_intents = {"necesita", "conviene", "numero_magico", "puesto_exacto", "visual", "puesto", "barras", "chances", "arbol", "ficha"}
    ya = acc.get("equipo") and detectar_equipo(acc["equipo"], cur)
    if intent in team_intents and not ya:
        lab, team, datos = _buscar_grupo_de(acc.get("equipo") or q)
        if lab:
            cargar_estado(*datos)
            acc["equipo"] = team
            pre = pre + [("info", f"Cambié al Grupo {lab}, donde juega {team}.")]
        elif st.session_state.get("ultimo_equipo") and not acc.get("equipo"):
            acc["equipo"] = st.session_state["ultimo_equipo"]  # seguir hablando del último equipo

    # Memoria de contexto: recordar el último equipo mencionado
    if acc.get("equipo"):
        st.session_state["ultimo_equipo"] = acc["equipo"]

    if intent != "porque":
        st.session_state["ULTIMO"] = {"intent": intent, "equipo": acc.get("equipo"),
                                      "n": acc.get("n"), "objetivo": acc.get("objetivo"), "q": q}
    return pre + ejecutar_accion(acc)


def render_blocks(blocks, prefix="x"):
    for i, b in enumerate(blocks):
        kind = b[0]
        if kind == "md":
            st.markdown(b[1])
        elif kind == "placa":
            if b[1]:
                st.markdown(b[1], unsafe_allow_html=True)
            else:
                st.image(b[2], use_container_width=True)
            st.download_button("Descargar imagen", b[2], file_name=b[3], mime="image/png", key=f"{prefix}_dl{i}")
        elif kind == "df":
            st.dataframe(b[1], use_container_width=True, hide_index=True)
            if len(b) > 2 and b[2]:
                st.caption(b[2])
        elif kind == "html":
            st.markdown(b[1], unsafe_allow_html=True)
        elif kind == "info":
            st.info(b[1])
        elif kind == "success":
            st.success(b[1])
        elif kind == "warning":
            st.warning(b[1])
        elif kind == "error":
            st.error(b[1])


# ─── CONFIG DEL LLM EN EL PANEL LATERAL ──────────────────────────────────────────
with st.sidebar:
    st.divider()
    st.subheader("🤖 Asistente (LLM)")
    st.session_state.LLM_ON = st.toggle(
        "Interpretar preguntas con Claude", value=st.session_state.LLM_ON,
        help="Si lo activás, entiende preguntas más libres. Las cuentas siempre las hace el motor.")
    if st.session_state.LLM_ON:
        st.session_state.LLM_KEY = st.text_input(
            "Anthropic API key", value=st.session_state.LLM_KEY, type="password", placeholder="sk-ant-...")
        st.session_state.LLM_MODEL = st.text_input(
            "Modelo", value=st.session_state.LLM_MODEL,
            help="Ej.: claude-haiku-4-5 (rápido y barato), claude-sonnet-4-6, claude-opus-4-8.")
        if not str(st.session_state.LLM_KEY).strip():
            st.caption("Sin key, uso el router por palabras clave.")
        if st.session_state.get("LLM_ERROR"):
            st.warning(f"Último error del asistente: {st.session_state['LLM_ERROR']}")
            st.caption("Si dice 'model'/'404', revisá el nombre del modelo. Si dice '401'/'authentication', es la API key. "
                       "El chat funciona igual por palabras clave (escribí «ayuda»).")
    if st.button("🧹 Limpiar conversación", use_container_width=True):
        st.session_state.chat = [{"role": "assistant", "blocks": [("md", BIENVENIDA)]}]
        st.rerun()


# ─── CHAT ────────────────────────────────────────────────────────────────────────
modo = "🤖 con Claude" if (st.session_state.LLM_ON and str(st.session_state.LLM_KEY).strip()) else "🔤 por palabras clave"
st.subheader(f"💬 Consultá los escenarios · {modo}")

_gs_tot = _tour_grupos()
if len(_gs_tot) > 1:
    st.caption(f"✅ Tenés **{len(_gs_tot)} grupos** cargados ({', '.join(_gs_tot)}). "
               "Preguntá por **cualquier** equipo: si es de otro grupo, cambio solo. "
               "Probá «¿en qué grupo está Brasil?» o «¿qué grupos hay?».")

if "chat" not in st.session_state:
    st.session_state.chat = [{"role": "assistant", "blocks": [("md", BIENVENIDA)]}]

for _mi, msg in enumerate(st.session_state.chat):
    with st.chat_message(msg["role"], avatar="⚽" if msg["role"] == "assistant" else None):
        render_blocks(msg["blocks"], prefix=f"m{_mi}")

if esc is not None and pendientes:
    with st.expander("🎮 Simulador: ¿qué pasa si…?  (elegí resultados y mirá cómo queda)"):
        _fixed = {}
        for _i, (_l, _v) in enumerate(pendientes, 1):
            _opt = st.selectbox(f"{_l} vs {_v}", ["— sin definir", f"Gana {_l}", "Empate", f"Gana {_v}"], key=f"sim{_i}")
            if _opt == f"Gana {_l}":   _fixed[_i] = "L"
            elif _opt == "Empate":     _fixed[_i] = "E"
            elif _opt == f"Gana {_v}": _fixed[_i] = "V"
        if _fixed:
            _jugsim, _rem = aplicar_resultados(equipos, jugados, pendientes, _fixed)
            st.dataframe(tabla(equipos, _jugsim), use_container_width=True, hide_index=True)
            st.markdown(previa_condicional_texto(equipos, jugados, pendientes, esc, _fixed))
        else:
            st.caption("Elegí al menos un resultado para ver el efecto.")

st.caption("Sugerencias rápidas:")
sug1 = [f"¿Cómo viene {equipos[0]}?", f"¿Qué necesita {equipos[0]}?", "¿De quién depende?", "Si terminara hoy"]
sug2 = [f"Contame el escenario de {equipos[0]}", "Relato del grupo", "Partido bisagra", "Ayuda"]
clic = None
for fila in (sug1, sug2):
    for c, s in zip(st.columns(len(fila)), fila):
        if c.button(s, use_container_width=True, key=f"sug_{s}"):
            clic = s

prompt = st.chat_input("Preguntá: «¿qué necesita España?», «¿en qué grupo está Brasil?», «equipos del grupo C»…")
consulta = prompt or clic
if consulta:
    st.session_state.chat.append({"role": "user", "blocks": [("md", consulta)]})
    try:
        bloques = responder(consulta)
    except Exception as e:
        bloques = [("error", f"Tuve un problema procesando esa consulta: {e}")]
    st.session_state.chat.append({"role": "assistant", "blocks": bloques})
    st.rerun()
