"""Pure-SQLite statistics layer. The MCP server is a thin wrapper around these functions."""
import difflib
import functools
import sqlite3

from .config import DB_PATH

TEAM_ALIASES = {
    "csk": "Chennai Super Kings", "mi": "Mumbai Indians",
    "rcb": "Royal Challengers Bengaluru", "rcb bengaluru": "Royal Challengers Bengaluru",
    "kkr": "Kolkata Knight Riders", "dc": "Delhi Capitals", "srh": "Sunrisers Hyderabad",
    "rr": "Rajasthan Royals", "pbks": "Punjab Kings", "gt": "Gujarat Titans",
    "lsg": "Lucknow Super Giants",
}
NON_BOWLER_WICKETS = ("run out", "retired hurt", "retired out", "obstructing the field")


def connect():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"{DB_PATH} not found. Run: python -m cricket_analyst.db --demo")
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


@functools.lru_cache(maxsize=4)
def _names(db_path: str):
    c = sqlite3.connect(db_path)
    rows = c.execute("SELECT batter FROM deliveries UNION SELECT bowler FROM deliveries").fetchall()
    c.close()
    return sorted({r[0] for r in rows if r[0]})


def resolve_player(name: str):
    """'Virat Kohli' -> 'V Kohli' (Cricsheet/Kaggle style) or exact match. Returns (name|None, note)."""
    names, lname = _names(str(DB_PATH)), name.lower().strip()
    for n in names:
        if n.lower() == lname:
            return n, None
    toks = lname.split()
    cands = [n for n in names if n.lower().split()[-1] == toks[-1]]
    if len(toks) > 1:
        cands = [n for n in cands if n[0].lower() == toks[0][0]] or cands
    if len(cands) == 1:
        return cands[0], None
    if len(cands) > 1:
        return None, f"Ambiguous player '{name}': {cands[:5]}"
    close = difflib.get_close_matches(name, names, 3, 0.75)
    return (close[0], None) if close else (None, f"Player '{name}' not found in dataset")


def resolve_team(name: str):
    key = name.lower().strip()
    key = TEAM_ALIASES.get(key, name)
    c = connect()
    teams = {r[0] for r in c.execute("SELECT team1 FROM matches UNION SELECT team2 FROM matches")}
    c.close()
    hit = [t for t in teams if key.lower() in t.lower()]
    return hit[0] if hit else None


def _filters(season_from, season_to, venue, fmt):
    w, p = [], []
    if season_from:
        w.append("AND m.season_year>=?"); p.append(int(season_from))
    if season_to:
        w.append("AND m.season_year<=?"); p.append(int(season_to))
    if venue:
        w.append("AND (m.venue LIKE ? OR m.city LIKE ?)"); p += [f"%{venue}%"] * 2
    if fmt:
        w.append("AND m.format=?"); p.append(fmt)
    return " ".join(w), p


def _meta():
    return {"dataset": str(DB_PATH.name), "note": "Derived from ball-by-ball data; verify coverage dates."}


def bat_points(runs, fours, sixes, out):
    bonus = 16 if runs >= 100 else 8 if runs >= 50 else 4 if runs >= 30 else 0
    return runs + fours + 2 * sixes + bonus - (2 if runs == 0 and out else 0)


def bowl_points(wkts, bowled_lbw, dots):
    haul = 16 if wkts >= 5 else 8 if wkts >= 4 else 0
    return 25 * wkts + 8 * bowled_lbw + haul + dots


def _batting(conn, player, wf, wp):
    sql = f"""SELECT d.match_id, m.date,
        SUM(d.batsman_runs) runs,
        SUM(CASE WHEN COALESCE(d.extras_type,'')!='wides' THEN 1 ELSE 0 END) balls,
        SUM(d.batsman_runs=4) fours, SUM(d.batsman_runs=6) sixes,
        MAX(CASE WHEN d.player_dismissed=d.batter THEN 1 ELSE 0 END) out
      FROM deliveries d JOIN matches m ON m.id=d.match_id
      WHERE d.batter=? {wf} GROUP BY d.match_id ORDER BY m.date"""
    return [dict(r) for r in conn.execute(sql, [player] + wp)]


def _bowling(conn, player, wf, wp):
    nb = "COALESCE(d.extras_type,'') NOT IN ('wides','noballs')"
    sql = f"""SELECT d.match_id, m.date,
        SUM(CASE WHEN {nb} THEN 1 ELSE 0 END) balls,
        SUM(CASE WHEN COALESCE(d.extras_type,'') NOT IN ('byes','legbyes') THEN d.total_runs ELSE 0 END) runs,
        SUM(CASE WHEN d.is_wicket=1 AND COALESCE(d.dismissal_kind,'') NOT IN
            ('run out','retired hurt','retired out','obstructing the field') THEN 1 ELSE 0 END) wkts,
        SUM(CASE WHEN d.is_wicket=1 AND d.dismissal_kind IN ('bowled','lbw') THEN 1 ELSE 0 END) bl,
        SUM(CASE WHEN d.total_runs=0 AND {nb} THEN 1 ELSE 0 END) dots
      FROM deliveries d JOIN matches m ON m.id=d.match_id
      WHERE d.bowler=? {wf} GROUP BY d.match_id ORDER BY m.date"""
    return [dict(r) for r in conn.execute(sql, [player] + wp)]


def _r(x, n=2):
    return None if x is None else round(x, n)


def _bat_summary(rows):
    if not rows:
        return None
    runs, balls = sum(r["runs"] for r in rows), sum(r["balls"] for r in rows)
    outs = sum(r["out"] for r in rows)
    return {"innings": len(rows), "runs": runs, "balls": balls, "not_outs": len(rows) - outs,
            "average": _r(runs / outs) if outs else None, "strike_rate": _r(100 * runs / balls) if balls else None,
            "fifties": sum(1 for r in rows if 50 <= r["runs"] < 100), "hundreds": sum(r["runs"] >= 100 for r in rows),
            "highest": max(r["runs"] for r in rows), "fours": sum(r["fours"] for r in rows),
            "sixes": sum(r["sixes"] for r in rows)}


def _bowl_summary(rows):
    if not rows:
        return None
    balls, runs, w = sum(r["balls"] for r in rows), sum(r["runs"] for r in rows), sum(r["wkts"] for r in rows)
    return {"matches": len(rows), "overs": f"{balls // 6}.{balls % 6}", "runs_conceded": runs, "wickets": w,
            "average": _r(runs / w) if w else None, "economy": _r(6 * runs / balls) if balls else None,
            "strike_rate": _r(balls / w) if w else None, "best_wickets": max(r["wkts"] for r in rows),
            "dot_ball_pct": _r(100 * sum(r["dots"] for r in rows) / balls, 1) if balls else None}


def _fantasy(bat_rows, bowl_rows):
    pts = {}
    for r in bat_rows:
        pts.setdefault(r["match_id"], [r["date"], 0])[1] += bat_points(r["runs"], r["fours"], r["sixes"], r["out"])
    for r in bowl_rows:
        pts.setdefault(r["match_id"], [r["date"], 0])[1] += bowl_points(r["wkts"], r["bl"], r["dots"])
    series = sorted(pts.values())
    vals = [v for _, v in series]
    if not vals:
        return None
    last5 = vals[-5:]
    return {"matches": len(vals), "avg_points": _r(sum(vals) / len(vals), 1),
            "avg_last5": _r(sum(last5) / len(last5), 1),
            "form_series": [{"date": d, "points": v} for d, v in series[-10:]]}


def player_stats(player, discipline="all", season_from=None, season_to=None, venue=None, fmt=None):
    conn = connect()
    name, err = resolve_player(player)
    if not name:
        return {"error": err}
    wf, wp = _filters(season_from, season_to, venue, fmt)
    br = _batting(conn, name, wf, wp) if discipline in ("all", "batting") else []
    bw = _bowling(conn, name, wf, wp) if discipline in ("all", "bowling") else []
    out = {"player": name, "query_name": player,
           "filters": {"season_from": season_from, "season_to": season_to, "venue": venue, "format": fmt},
           "meta": _meta()}
    if discipline in ("all", "batting"):
        out["batting"] = _bat_summary(br)
    if discipline in ("all", "bowling"):
        out["bowling"] = _bowl_summary(bw)
    if discipline == "all":
        out["fantasy"] = _fantasy(br, bw)
    conn.close()
    return out


def head_to_head(kind, a, b, season_from=None, season_to=None, venue=None):
    conn = connect()
    wf, wp = _filters(season_from, season_to, venue, None)
    if kind == "team":
        ta, tb = resolve_team(a), resolve_team(b)
        if not (ta and tb):
            return {"error": f"Unknown team(s): {a}, {b}"}
        rows = conn.execute(f"""SELECT m.date, m.venue, m.winner FROM matches m
            WHERE ((m.team1=? AND m.team2=?) OR (m.team1=? AND m.team2=?)) {wf}
            ORDER BY m.date""", [ta, tb, tb, ta] + wp).fetchall()
        return {"kind": "team", "team_a": ta, "team_b": tb, "matches": len(rows),
                "wins": {ta: sum(r["winner"] == ta for r in rows), tb: sum(r["winner"] == tb for r in rows),
                         "no_result": sum(r["winner"] is None for r in rows)},
                "last_5": [dict(r) for r in rows[-5:]], "meta": _meta()}
    if kind == "batter_vs_bowler":
        bat, e1 = resolve_player(a)
        bowl, e2 = resolve_player(b)
        if not (bat and bowl):
            return {"error": e1 or e2}
        r = conn.execute(f"""SELECT SUM(d.batsman_runs) runs,
            SUM(CASE WHEN COALESCE(d.extras_type,'')!='wides' THEN 1 ELSE 0 END) balls,
            SUM(d.is_wicket=1 AND d.player_dismissed=d.batter
                AND COALESCE(d.dismissal_kind,'') NOT IN ('run out','retired hurt')) dismissals,
            SUM(d.batsman_runs=0) dots, SUM(d.batsman_runs=4) fours, SUM(d.batsman_runs=6) sixes
          FROM deliveries d JOIN matches m ON m.id=d.match_id
          WHERE d.batter=? AND d.bowler=? {wf}""", [bat, bowl] + wp).fetchone()
        balls = r["balls"] or 0
        return {"kind": "batter_vs_bowler", "batter": bat, "bowler": bowl, "balls": balls,
                "runs": r["runs"] or 0, "dismissals": r["dismissals"] or 0, "dots": r["dots"] or 0,
                "fours": r["fours"] or 0, "sixes": r["sixes"] or 0,
                "strike_rate": _r(100 * (r["runs"] or 0) / balls) if balls else None,
                "small_sample_warning": balls < 30, "meta": _meta()}
    return {"error": "kind must be 'team' or 'batter_vs_bowler'"}


def venue_stats(venue, season_from=None, season_to=None, fmt=None):
    conn = connect()
    wf, wp = _filters(season_from, season_to, venue, fmt)
    ms = conn.execute(f"SELECT * FROM matches m WHERE 1=1 {wf}", wp).fetchall()
    if not ms:
        vs = [r[0] for r in conn.execute("SELECT DISTINCT venue FROM matches").fetchall()][:15]
        return {"error": f"No matches at '{venue}'", "known_venues": vs}
    inn = conn.execute(f"""SELECT m.id mid, d.inning, MIN(d.batting_team) team, SUM(d.total_runs) total
        FROM deliveries d JOIN matches m ON m.id=d.match_id
        WHERE d.inning IN (1,2) {wf} GROUP BY m.id, d.inning""", wp).fetchall()
    first = [r["total"] for r in inn if r["inning"] == 1]
    second = [r["total"] for r in inn if r["inning"] == 2]
    first_team = {r["mid"]: r["team"] for r in inn if r["inning"] == 1}
    decided = [m for m in ms if m["winner"]]
    toss_won = [m for m in decided if m["toss_winner"] == m["winner"]]
    bat_first_wins = [m for m in decided if first_team.get(m["id"]) == m["winner"]]
    avg = lambda xs: _r(sum(xs) / len(xs), 1) if xs else None
    typ = conn.execute(f"""SELECT bt.type, COUNT(*) n FROM deliveries d
        JOIN matches m ON m.id=d.match_id JOIN bowler_types bt ON bt.bowler=d.bowler
        WHERE d.is_wicket=1 AND d.inning IN (1,2)
          AND COALESCE(d.dismissal_kind,'') NOT IN ('run out','retired hurt','retired out') {wf}
        GROUP BY bt.type""", wp).fetchall()
    tot = sum(r["n"] for r in typ)
    return {"venue": venue, "matches": len(ms),
            "avg_first_innings": avg(first), "avg_second_innings": avg(second),
            "highest_total": max(first + second), "lowest_total": min(first + second),
            "bat_first_win_pct": _r(100 * len(bat_first_wins) / len(decided), 1) if decided else None,
            "toss_winner_won_match_pct": _r(100 * len(toss_won) / len(decided), 1) if decided else None,
            "chose_to_field_pct": _r(100 * sum(m["toss_decision"] == "field" for m in ms) / len(ms), 1),
            "wickets_pace_spin_pct": ({r["type"]: _r(100 * r["n"] / tot, 1) for r in typ} if tot else None),
            "meta": _meta()}
