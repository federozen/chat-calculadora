"""Motor exacto de escenarios por resultados para la LPF.

Usa ``scipy.optimize.milp`` cuando está disponible. No modela marcadores futuros:
los empates en puntos se tratan de forma favorable o desfavorable según la pregunta.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, Mapping, Sequence

import numpy as np

try:
    from scipy.optimize import Bounds, LinearConstraint, milp
    from scipy.sparse import lil_matrix
    SCIPY_MILP = True
except Exception:  # pragma: no cover - fallback documentado
    SCIPY_MILP = False

from lpf_models import PointLadderRow

OUTCOMES = ("L", "E", "V")
POINTS_HOME = (3, 1, 0)
POINTS_AWAY = (0, 1, 3)


@dataclass
class SolverResult:
    feasible: bool
    objective: float | None = None
    outcomes: dict[tuple[str, str], str] | None = None
    message: str = ""


def _points(value: object) -> int:
    if isinstance(value, Mapping):
        return int(value.get("pts", 0))
    return int(value)


def _normalize_matches(matches: Iterable[tuple[str, str]]) -> tuple[tuple[str, str], ...]:
    return tuple((str(a), str(b)) for a, b in matches)


def _build_model(
    base: Mapping[str, object],
    matches: Sequence[tuple[str, str]],
    team: str,
    target_final: int,
    cutoff: int,
    mode: str,
    fixed: Mapping[tuple[str, str], str] | None = None,
    optimize_rank: str | None = None,
) -> SolverResult:
    if not SCIPY_MILP:
        return SolverResult(False, message="scipy.optimize.milp no está disponible")
    if team not in base:
        return SolverResult(False, message="equipo desconocido")
    teams = list(base)
    rivals = [t for t in teams if t != team]
    matches = list(matches)
    fixed = dict(fixed or {})
    m, r = len(matches), len(rivals)
    nvars = 3 * m + r
    if nvars == 0:
        rank_bad = sum(_points(base[x]) >= target_final for x in rivals)
        if mode == "fail":
            return SolverResult(rank_bad >= cutoff)
        rank_strict = sum(_points(base[x]) > target_final for x in rivals)
        return SolverResult(rank_strict <= cutoff - 1)

    # Coeficientes de puntos ganados por cada equipo.
    gains = {t: np.zeros(nvars) for t in teams}
    for j, (home, away) in enumerate(matches):
        for o in range(3):
            gains.setdefault(home, np.zeros(nvars))[3*j + o] += POINTS_HOME[o]
            gains.setdefault(away, np.zeros(nvars))[3*j + o] += POINTS_AWAY[o]

    rows: list[tuple[np.ndarray, float, float]] = []
    # Un solo resultado por partido.
    for j, match in enumerate(matches):
        row = np.zeros(nvars)
        row[3*j:3*j+3] = 1
        rows.append((row, 1, 1))
        if match in fixed:
            wanted = OUTCOMES.index(fixed[match])
            for o in range(3):
                if o != wanted:
                    rfix = np.zeros(nvars); rfix[3*j+o] = 1
                    rows.append((rfix, 0, 0))

    # El equipo objetivo termina exactamente con target_final.
    need = target_final - _points(base[team])
    rows.append((gains.get(team, np.zeros(nvars)), need, need))

    max_diff = max(12, 3 * len(matches) + max((_points(v) for v in base.values()), default=0) + 5)
    y_start = 3 * m
    for i, rival in enumerate(rivals):
        y = y_start + i
        diff = gains.get(rival, np.zeros(nvars))
        diff = diff - gains.get(team, np.zeros(nvars))
        base_diff = _points(base[rival]) - _points(base[team])
        if mode in ("qualify", "best_rank"):
            # y=1 <=> rival termina estrictamente por encima.
            row1 = diff.copy(); row1[y] -= max_diff
            rows.append((row1, -np.inf, -base_diff))       # diff+base <= M*y
            row2 = -diff.copy(); row2[y] += max_diff
            rows.append((row2, -np.inf, max_diff - 1 + base_diff))
        else:
            # y=1 <=> rival termina igualado o por encima (desempate adverso).
            row1 = diff.copy(); row1[y] -= max_diff
            rows.append((row1, -np.inf, -1 - base_diff))   # y=0 => diff+base <= -1
            row2 = -diff.copy(); row2[y] += max_diff
            rows.append((row2, -np.inf, max_diff + base_diff))

    count = np.zeros(nvars); count[y_start:] = 1
    if mode == "qualify":
        rows.append((count, -np.inf, cutoff - 1))
    elif mode == "fail":
        rows.append((count, cutoff, np.inf))

    A = lil_matrix((len(rows), nvars), dtype=float)
    lb = np.empty(len(rows)); ub = np.empty(len(rows))
    for i, (row, low, high) in enumerate(rows):
        A[i, :] = row
        lb[i], ub[i] = low, high

    c = np.zeros(nvars)
    if optimize_rank == "best":
        c[y_start:] = 1
    elif optimize_rank == "worst":
        c[y_start:] = -1
    result = milp(
        c=c,
        integrality=np.ones(nvars),
        bounds=Bounds(np.zeros(nvars), np.ones(nvars)),
        constraints=LinearConstraint(A.tocsr(), lb, ub),
        options={"time_limit": 12.0, "mip_rel_gap": 0.0},
    )
    if not result.success or result.x is None:
        return SolverResult(False, message=str(result.message))
    outcomes: dict[tuple[str, str], str] = {}
    for j, match in enumerate(matches):
        outcomes[match] = OUTCOMES[int(np.argmax(result.x[3*j:3*j+3]))]
    objective = float(result.fun) if result.fun is not None else None
    return SolverResult(True, objective, outcomes, str(result.message))


def can_qualify_with_points(base, matches, team, cutoff, final_points, fixed=None) -> SolverResult:
    return _build_model(base, _normalize_matches(matches), team, int(final_points), int(cutoff), "qualify", fixed)


def can_fail_with_points(base, matches, team, cutoff, final_points, fixed=None) -> SolverResult:
    return _build_model(base, _normalize_matches(matches), team, int(final_points), int(cutoff), "fail", fixed)


def exact_rank_bounds_with_points(base, matches, team, final_points, fixed=None) -> tuple[int, int] | None:
    best = _build_model(base, _normalize_matches(matches), team, int(final_points), len(base), "best_rank", fixed, "best")
    worst = _build_model(base, _normalize_matches(matches), team, int(final_points), len(base), "worst_rank", fixed, "worst")
    if not best.feasible or not worst.feasible:
        return None
    best_above = int(round(best.objective or 0))
    worst_above = int(round(-(worst.objective or 0)))
    return best_above + 1, worst_above + 1


def reachable_point_totals(current: int, games_left: int) -> list[int]:
    totals = set()
    for wins in range(games_left + 1):
        for draws in range(games_left - wins + 1):
            totals.add(current + 3 * wins + draws)
    return sorted(totals)


def _describe_outcomes(outcomes: Mapping[tuple[str, str], str] | None, team: str, limit: int = 5) -> list[str]:
    if not outcomes:
        return []
    descriptions = []
    for (home, away), result in outcomes.items():
        if team in (home, away):
            continue
        if result == "L":
            descriptions.append(f"gana {home} ante {away}")
        elif result == "V":
            descriptions.append(f"gana {away} ante {home}")
        else:
            descriptions.append(f"empatan {home} y {away}")
        if len(descriptions) >= limit:
            break
    return descriptions


def point_ladder(
    base: Mapping[str, object],
    matches: Iterable[tuple[str, str]],
    team: str,
    cutoff: int,
    *,
    max_rows: int = 8,
    max_matches: int = 100,
) -> dict[str, object]:
    matches = _normalize_matches(matches)
    current = _points(base[team])
    games_left = sum(team in match for match in matches)
    reachable = reachable_point_totals(current, games_left)
    if not SCIPY_MILP or len(matches) > max_matches:
        return {
            "available": False,
            "reason": "El motor exacto se reserva para ventanas de hasta 100 partidos; se usa la garantía conservadora.",
            "minimum_possible": None,
            "guarantee": None,
            "rows": [],
        }
    statuses: list[PointLadderRow] = []
    minimum = None
    guarantee = None
    for pts in reachable:
        q = can_qualify_with_points(base, matches, team, cutoff, pts)
        if not q.feasible:
            continue
        minimum = pts if minimum is None else minimum
        fail = can_fail_with_points(base, matches, team, cutoff, pts)
        guaranteed = not fail.feasible
        if guaranteed and guarantee is None:
            guarantee = pts
        status = "Garantía matemática" if guaranteed else "Clasificación condicionada"
        statuses.append(PointLadderRow(
            final_points=pts,
            status=status,
            can_qualify=True,
            can_fail=fail.feasible,
            guaranteed=guaranteed,
            example=[] if guaranteed else _describe_outcomes(q.outcomes, team),
            note=("No depende de otros resultados ni del desempate." if guaranteed else
                  "Existe al menos un camino de clasificación y también un escenario de eliminación."),
        ))
        if guarantee is not None and pts >= guarantee + 3:
            break
    # Mantener los puntos cercanos a la frontera, no toda la temporada.
    if len(statuses) > max_rows:
        pivot = next((i for i, row in enumerate(statuses) if row.guaranteed), len(statuses) - 1)
        start = max(0, pivot - max_rows + 2)
        statuses = statuses[start:start + max_rows]
    return {
        "available": True,
        "minimum_possible": minimum,
        "guarantee": guarantee,
        "rows": statuses,
        "solver": "scipy.optimize.milp",
    }


def exact_result_scenarios(
    base: Mapping[str, object],
    games: Sequence[tuple[str, str]],
    team: str,
    own_match: tuple[str, str],
    cutoff: int,
) -> list[dict[str, object]]:
    """Gana/empata/pierde en una ventana que puede contener postergados.

    Si el equipo juega otro partido dentro de la misma ventana, ese segundo partido
    queda libre y es incorporado al rango.
    """
    current = _points(base[team])
    is_home = own_match[0] == team
    labels = (("Gana", "L" if is_home else "V", 3), ("Empata", "E", 1), ("Pierde", "V" if is_home else "L", 0))
    rows = []
    for label, code, gain in labels:
        fixed = {own_match: code}
        # El puntaje final de la ventana también depende de un eventual segundo partido.
        other_games = sum(team in match and match != own_match for match in games)
        possible = reachable_point_totals(current + gain, other_games)
        rank_bounds = []
        can_enter = False
        can_fail = False
        for pts in possible:
            rb = exact_rank_bounds_with_points(base, games, team, pts, fixed)
            if rb:
                rank_bounds.append(rb)
            can_enter = can_enter or can_qualify_with_points(base, games, team, cutoff, pts, fixed).feasible
            can_fail = can_fail or can_fail_with_points(base, games, team, cutoff, pts, fixed).feasible
        rows.append({
            "result": label,
            "points_min": min(possible),
            "points_max": max(possible),
            "best_rank": min((r[0] for r in rank_bounds), default=None),
            "worst_rank": max((r[1] for r in rank_bounds), default=None),
            "can_enter": can_enter,
            "can_fail": can_fail,
        })
    return rows


def _fixed_gain_for_team(team: str, fixed: Mapping[tuple[str, str], str]) -> int:
    gain = 0
    for (home, away), outcome in fixed.items():
        if team == home:
            gain += 3 if outcome == "L" else 1 if outcome == "E" else 0
        elif team == away:
            gain += 3 if outcome == "V" else 1 if outcome == "E" else 0
    return gain


def scenario_rank_bounds(
    base: Mapping[str, object],
    games: Sequence[tuple[str, str]],
    team: str,
    fixed: Mapping[tuple[str, str], str] | None = None,
) -> dict[str, object]:
    """Rango exacto de puesto para una ventana parcialmente fijada.

    Los partidos sin resultado quedan abiertos. El motor no inventa marcadores:
    cuando hay igualdad en puntos, el mejor y el peor puesto contemplan un
    desempate favorable o adverso.
    """
    fixed = dict(fixed or {})
    games = _normalize_matches(games)
    current = _points(base[team])
    fixed_gain = _fixed_gain_for_team(team, fixed)
    open_team_games = sum(team in match and match not in fixed for match in games)
    totals = reachable_point_totals(current + fixed_gain, open_team_games)
    bounds: list[tuple[int, int, int]] = []
    for final_points in totals:
        rb = exact_rank_bounds_with_points(base, games, team, final_points, fixed)
        if rb is not None:
            bounds.append((final_points, rb[0], rb[1]))
    return {
        "available": bool(bounds),
        "points_min": min((row[0] for row in bounds), default=None),
        "points_max": max((row[0] for row in bounds), default=None),
        "best_rank": min((row[1] for row in bounds), default=None),
        "worst_rank": max((row[2] for row in bounds), default=None),
        "by_points": bounds,
    }


def best_worst_window_scenarios(
    base: Mapping[str, object],
    games: Sequence[tuple[str, str]],
    team: str,
    fixed: Mapping[tuple[str, str], str] | None = None,
) -> dict[str, object]:
    """Devuelve un ejemplo concreto del mejor y peor caso de una ventana.

    El resultado es exacto por puntos. Los desempates futuros no se resuelven con
    marcadores inventados: el mejor caso supone desempate favorable y el peor,
    desfavorable.
    """
    fixed = dict(fixed or {})
    games = _normalize_matches(games)
    current = _points(base[team])
    fixed_gain = _fixed_gain_for_team(team, fixed)
    open_team_games = sum(team in match and match not in fixed for match in games)
    totals = reachable_point_totals(current + fixed_gain, open_team_games)
    best_row = None
    worst_row = None
    for final_points in totals:
        best = _build_model(base, games, team, final_points, len(base), "best_rank", fixed, "best")
        if best.feasible:
            rank = int(round(best.objective or 0)) + 1
            candidate = {
                "rank": rank,
                "final_points": final_points,
                "outcomes": best.outcomes or {},
            }
            if best_row is None or (rank, -final_points) < (best_row["rank"], -best_row["final_points"]):
                best_row = candidate
        worst = _build_model(base, games, team, final_points, len(base), "worst_rank", fixed, "worst")
        if worst.feasible:
            above = int(round(-(worst.objective or 0)))
            rank = above + 1
            candidate = {
                "rank": rank,
                "final_points": final_points,
                "outcomes": worst.outcomes or {},
            }
            if worst_row is None or (rank, -final_points) > (worst_row["rank"], -worst_row["final_points"]):
                worst_row = candidate
    return {
        "available": best_row is not None and worst_row is not None,
        "best": best_row,
        "worst": worst_row,
    }
