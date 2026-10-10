"""Deterministic fantasy-team construction + validation (no LLM => no hallucinated constraints).

The Team Builder makes one move per call (initial pick, then one repair swap per iteration);
the Validator is the single source of truth for constraints. That is what lets the
Builder<->Validator loop converge and report honestly when it can't.
"""
from collections import Counter
from dataclasses import dataclass, replace

from .config import PLAYERS_CSV, FantasyRules


@dataclass(frozen=True)
class Player:
    name: str
    team: str
    role: str
    credits: float
    proj: float = 0.0
    note: str = ""


def project(avg_all, avg_last5, venue_avg=None, venue_n=0, default=20.0):
    """Blend career, recent form and venue history into projected fantasy points."""
    if avg_all is None:
        return default, "no history in dataset; default projection"
    parts = [(0.5, avg_last5 if avg_last5 is not None else avg_all), (0.3, avg_all)]
    if venue_avg is not None and venue_n >= 3:
        parts.append((0.2, venue_avg))
    wsum = sum(w for w, _ in parts)
    val = sum(w * v for w, v in parts) / wsum
    note = f"last-5 avg {avg_last5:.0f}, career avg {avg_all:.0f} pts"
    if venue_avg is not None and venue_n >= 3:
        note += f", {venue_avg:.0f} at venue ({venue_n} m)"
    return round(val, 1), note


def violations(sel, rules: FantasyRules):
    v = []
    if len({p.name for p in sel}) != len(sel):
        v.append("DUPLICATE: a player is selected twice")
    if len(sel) != rules.size:
        v.append(f"SIZE: {len(sel)} players selected, need {rules.size}")
    cost = sum(p.credits for p in sel)
    if cost > rules.budget + 1e-9:
        v.append(f"BUDGET: {cost:.1f} credits > {rules.budget:.1f}")
    rc = Counter(p.role for p in sel)
    for role, (lo, hi) in rules.roles.items():
        if rc[role] < lo:
            v.append(f"ROLE_MIN: {role} {rc[role]} < {lo}")
        if rc[role] > hi:
            v.append(f"ROLE_MAX: {role} {rc[role]} > {hi}")
    for team, n in Counter(p.team for p in sel).items():
        if n > rules.max_per_team:
            v.append(f"TEAM_CAP: {team} {n} > {rules.max_per_team}")
    return v


def _excess(sel, rules):
    return max(0.0, sum(p.credits for p in sel) - rules.budget)


def _initial(pool, rules):
    sel, tc = [], Counter()
    by_proj = sorted(pool, key=lambda p: -p.proj)
    for role, (lo, _) in rules.roles.items():           # role minimums first
        for p in [p for p in by_proj if p.role == role][:lo]:
            if tc[p.team] < rules.max_per_team:
                sel.append(p); tc[p.team] += 1
    rc = Counter(p.role for p in sel)
    for p in by_proj:                                    # then best remaining
        if len(sel) >= rules.size:
            break
        if p in sel or rc[p.role] >= rules.roles[p.role][1] or tc[p.team] >= rules.max_per_team:
            continue
        sel.append(p); rc[p.role] += 1; tc[p.team] += 1
    return sel


def _repair_step(sel, pool, rules):
    """Apply the single best swap that reduces violations / budget excess."""
    before_v, before_x = len(violations(sel, rules)), _excess(sel, rules)
    best = None
    for out in sel:
        for inn in pool:
            if inn in sel:
                continue
            cand = [inn if p is out else p for p in sel]
            nv, nx = len(violations(cand, rules)), _excess(cand, rules)
            if nv > before_v or (nv == before_v and nx >= before_x):
                continue                                  # no progress
            saved = out.credits - inn.credits
            lost = out.proj - inn.proj
            cost_of_fix = lost / saved if (saved > 0 and before_x > 0) else lost
            key = (nv, cost_of_fix)
            if best is None or key < best[0]:
                best = (key, cand)
    return best[1] if best else sel


def _improve(sel, pool, rules):
    """Hill-climb: single swaps that keep the team valid and add projected points."""
    while True:
        base = sum(p.proj for p in sel)
        best = None
        for out in sel:
            for inn in pool:
                if inn in sel:
                    continue
                cand = [inn if p is out else p for p in sel]
                gain = sum(p.proj for p in cand) - base
                if gain > 1e-9 and not violations(cand, rules) and (best is None or gain > best[0]):
                    best = (gain, cand)
        if not best:
            return sel
        sel = best[1]


def build_team(pool, rules: FantasyRules, prev=None):
    """One Team Builder step. First call = greedy pick; later calls = one repair swap."""
    sel = _initial(pool, rules) if prev is None else _repair_step(list(prev), pool, rules)
    if not violations(sel, rules):
        sel = _improve(sel, pool, rules)
    return sel


def pick_leaders(sel):
    ranked = sorted(sel, key=lambda p: -p.proj)
    return ranked[0], ranked[1]


def load_pool(path=PLAYERS_CSV):
    """players.csv columns: player,team,role(WK|BAT|AR|BOWL),credits. Credits come from your fantasy platform."""
    import csv
    with open(path, newline="") as f:
        return [Player(r["player"].strip(), r["team"].strip(), r["role"].strip().upper(), float(r["credits"]))
                for r in csv.DictReader(f)]
