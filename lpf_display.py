"""Presentacion editorial de nombres y tablas de la LPF.

Los calculos conservan los nombres canonicos completos. Este modulo solo cambia
la forma en que se muestran en pantalla para usar las denominaciones habituales
en el futbol argentino y evitar que una abreviatura altere cruces, fixtures o
comparaciones internas.
"""

from __future__ import annotations

from typing import Any


EDITORIAL_TEAM_NAMES: dict[str, str] = {
    "Argentinos Juniors": "Argentinos",
    "Barracas Central": "Barracas",
    "Boca Juniors": "Boca",
    "Defensa y Justicia": "Defensa",
    "Deportivo Riestra": "Riestra",
    "Estudiantes de La Plata": "Estudiantes",
    "Estudiantes de Río Cuarto": "Estudiantes (RC)",
    "Gimnasia La Plata": "Gimnasia",
    "Gimnasia de Mendoza": "Gimnasia (M)",
    "Newell's Old Boys": "Newell's",
    "River Plate": "River",
    "Vélez Sarsfield": "Vélez",
}


def display_team(value: Any) -> str:
    """Devuelve el nombre editorial sin modificar la clave canonica interna."""
    text = str(value or "")
    return EDITORIAL_TEAM_NAMES.get(text, text)


def editorialize_text(value: Any) -> Any:
    """Reemplaza nombres canonicos dentro de un texto visible."""
    if not isinstance(value, str):
        return value
    text = value
    for canonical in sorted(EDITORIAL_TEAM_NAMES, key=len, reverse=True):
        text = text.replace(canonical, EDITORIAL_TEAM_NAMES[canonical])
    return text


def editorialize_frame(value: Any) -> Any:
    """Crea una copia de un DataFrame/Series con nombres editoriales visibles."""
    try:
        import pandas as pd
    except ImportError:
        return value

    if isinstance(value, pd.DataFrame):
        frame = value.copy()
        frame.columns = [editorialize_text(column) if isinstance(column, str) else column for column in frame.columns]
        if frame.index.dtype == "object":
            frame.index = [editorialize_text(item) if isinstance(item, str) else item for item in frame.index]
        for column in frame.columns:
            if frame[column].dtype == "object":
                frame[column] = frame[column].map(
                    lambda item: editorialize_text(item) if isinstance(item, str) else item
                )
        return frame

    if isinstance(value, pd.Series):
        series = value.copy()
        if series.dtype == "object":
            series = series.map(lambda item: editorialize_text(item) if isinstance(item, str) else item)
        return series

    return value


def editorialize_spec(spec: Any) -> Any:
    """Copia una especificacion de placa/tabla y editorializa sus textos."""
    if not isinstance(spec, dict):
        return spec
    out = dict(spec)
    for key in ("titulo", "corner", "footer"):
        if key in out:
            out[key] = editorialize_text(out[key])
    for key in ("col_headers", "row_headers"):
        if isinstance(out.get(key), list):
            out[key] = [editorialize_text(item) for item in out[key]]
    if isinstance(out.get("leyenda"), list):
        legend = []
        for item in out["leyenda"]:
            if isinstance(item, tuple) and len(item) == 2:
                color, label = item
                legend.append((color, editorialize_text(label)))
            else:
                legend.append(item)
        out["leyenda"] = legend
    if isinstance(out.get("cells"), list):
        new_rows = []
        for row in out["cells"]:
            new_row = []
            for cell in row:
                if isinstance(cell, tuple) and len(cell) == 2:
                    new_row.append((editorialize_text(cell[0]), cell[1]))
                else:
                    new_row.append(cell)
            new_rows.append(new_row)
        out["cells"] = new_rows
    return out
