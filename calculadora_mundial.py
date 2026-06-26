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
    cw, rhw, rht, headh, titleh = 2.5, 2.6, 0.66, 0.74, 0.6
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
            ax.text(x + cw / 2, y + rht / 2, str(text), fontsize=12, fontweight="bold",
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
        part = base + [(l, v, int(rng.poisson(lam[l])), int(rng.poisson(lam[v]))) for (l, v) in pendientes]
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

_RE_HEADER = re.compile(r"^\s*(grupo|group|gpo)\s*[:.]?\s*([A-Za-z0-9]+)\s*$", re.I)

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

    st.divider()

    # Cargar datos
    st.subheader("📥 Cargar datos")
    modo_carga = st.radio("Fuente", ["API football-data.org", "Pegar texto"], label_visibility="collapsed")

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
        if E.get("esc") is None:
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


AYUDA_MD = """**¿Qué puedo responder?** Por ejemplo:

- **¿Qué necesita España?** — qué tiene que pasar para clasificar (y si puede, para ser campeón / mejor tercero).
- **¿Qué le conviene a Uruguay?** — qué resultado propio le sirve y qué hinchar en los otros partidos.
- **¿En qué grupo está Brasil?** · **Equipos del grupo C** · **¿Qué grupos hay?**
- **¿De quién depende?** (si cada equipo depende de sí mismo o necesita ayuda) · **Si terminara hoy** (quién pasa con la tabla actual)
- **¿Puede ser campeón Cabo Verde?** · **¿Qué necesita Arabia para no descender?**
- **Tabla** · **Panorama** · **Probabilidades** · **Número mágico de España** · **Asegurados**

Podés encadenar sin repetir el equipo: *«¿qué necesita Uruguay?»* y después *«¿y qué le conviene?»*.
Si preguntás por un equipo de otro grupo, **cambio solo** a ese grupo. Y si a un equipo le quedan
varios partidos, te respondo por **puntos** (con cuántos clasifica)."""

AYUDA_LIGA = """Esto es una **liga** (muchas fechas): el detalle gol por gol no se puede calcular, así que trabajo **por puntos**:

- **Tabla** · **Si terminara hoy** (quién entra a cada zona con la tabla actual)
- **Número mágico de River** · **¿Qué necesita River?** (cuántos puntos para asegurar)
- **Máximos** (techo de cada uno) · **Asegurados** (quién está adentro / sin chances)
- **Probabilidades** (estimadas por simulación)

Ajustá cuántos entran a cada zona en el panel lateral (**Clasifican directos**)."""

BIENVENIDA = ("👋 Soy la **calculadora de escenarios**. Preguntame en lenguaje natural: "
              "*«¿qué necesita España?»*, *«¿en qué grupo está Brasil?»*, *«equipos del grupo C»*, "
              "*«tabla»*… Si no te acordás el grupo de un equipo, preguntá igual y lo busco. "
              "Escribí **ayuda** para ver todo.")


# ─── EJECUTOR DETERMINÍSTICO (las cuentas las hace el motor, nunca el LLM) ─────────
def ejecutar_accion(acc):
    intent = acc.get("intent")
    equipo = acc.get("equipo")
    objetivo = acc.get("objetivo")
    n = acc.get("n")
    E = st.session_state.ESTADO
    eqs, jug, pen, esc = E["equipos"], E["jugados"], E["pendientes"], E["esc"]
    if equipo and equipo not in eqs:
        equipo = detectar_equipo(equipo, eqs)

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
            return [("md", "Estimación por simulación (Poisson, 8.000 sorteos)."),
                    ("df", probabilidades(eqs, jug, pen), "Probabilidades")]
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
        return [("md", "Probabilidades estimadas por simulación (Poisson, ~8.000 sorteos). Es una estimación, no la cuenta exacta."),
                ("df", probabilidades(eqs, jug, pen), "Probabilidades")]
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
    m = _re.search(r"top\s*(\d+)|primeros?\s*(\d+)|(\d+)\s*primeros|puesto\s*(\d+)|(\d+)\s*[oº]", qn)
    n_det = int(next(g for g in m.groups() if g)) if m else None
    mg = _re.search(r"grupo\s+([a-l])\b", qn)

    if has("ayuda", "help", "que puedo", "como funciona"):
        return {"intent": "ayuda"}
    if has("relato", "contame", "para la nota", "escribime", "escribi ", "narra", "narrá", "parrafo", "párrafo", "escenario escrito", "resumen escrito", "resumime", "redacta"):
        return {"intent": "relato", "equipo": team}
    if has("visual", "grilla", "matriz", "cuadro de escenarios", "mapa de escenarios", "tabla de escenarios", "grafic", "placa"):
        return {"intent": "visual", "equipo": team}
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
        'visual, comparar, puesto, mapa, ayuda]\n'
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
    if usar_llm:
        try:
            acc, intro = _llm_parse(q)
        except Exception as e:
            acc = _parse_kw(q)
            st.toast(f"LLM no disponible ({str(e)[:50]}…); uso el router por palabras.")
    else:
        acc = _parse_kw(q)

    pre = [("md", f"_{intro}_")] if intro else []
    intent = acc.get("intent")

    if intent == "listar_grupos":
        return pre + _bloques_listar_grupos()
    if intent == "ver_grupo":
        return pre + _bloques_ver_grupo(acc.get("grupo"))
    if intent == "buscar_equipo":
        return pre + _bloques_buscar_equipo(acc.get("equipo") or q)

    # Cambio automático de grupo si el equipo no está en el grupo cargado
    cur = st.session_state.ESTADO["equipos"]
    team_intents = {"necesita", "conviene", "numero_magico", "puesto_exacto", "visual", "puesto"}
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

    return pre + ejecutar_accion(acc)


def render_blocks(blocks, prefix="x"):
    for i, b in enumerate(blocks):
        kind = b[0]
        if kind == "md":
            st.markdown(b[1])
        elif kind == "placa":
            st.markdown(b[1], unsafe_allow_html=True)
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

st.caption("Sugerencias rápidas:")
sug = [f"¿Qué necesita {equipos[0]}?", "¿De quién depende?", "Si terminara hoy",
       f"¿Qué le conviene a {equipos[1]}?", "¿Qué grupos hay?", "Ayuda"]
clic = None
for c, s in zip(st.columns(len(sug)), sug):
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
