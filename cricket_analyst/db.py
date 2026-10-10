"""SQLite schema + loaders.

Usage:
  python -m cricket_analyst.db --demo
  python -m cricket_analyst.db --matches matches.csv --deliveries deliveries.csv   # Kaggle IPL dataset
Optional: data/bowler_types.csv (bowler,type) with type in {pace,spin} enables the pace/spin split.
"""
import argparse
import csv
import hashlib
import json
import sqlite3
from pathlib import Path

import pandas as pd

from .config import DATA_DIR, DB_PATH, PLAYERS_CSV

SCHEMA = """
DROP TABLE IF EXISTS matches; DROP TABLE IF EXISTS deliveries; DROP TABLE IF EXISTS bowler_types;
CREATE TABLE matches(id INTEGER PRIMARY KEY, season TEXT, season_year INTEGER, date TEXT,
  venue TEXT, city TEXT, format TEXT, team1 TEXT, team2 TEXT, toss_winner TEXT,
  toss_decision TEXT, winner TEXT);
CREATE TABLE deliveries(match_id INTEGER, inning INTEGER, batting_team TEXT, bowling_team TEXT,
  over INTEGER, ball INTEGER, batter TEXT, bowler TEXT, non_striker TEXT, batsman_runs INTEGER,
  extra_runs INTEGER, total_runs INTEGER, extras_type TEXT, is_wicket INTEGER,
  player_dismissed TEXT, dismissal_kind TEXT);
CREATE TABLE bowler_types(bowler TEXT PRIMARY KEY, type TEXT);
CREATE INDEX ix_d_batter ON deliveries(batter); CREATE INDEX ix_d_bowler ON deliveries(bowler);
CREATE INDEX ix_d_match ON deliveries(match_id); CREATE INDEX ix_m_venue ON matches(venue);
"""

DELIVERY_COLS = ["match_id", "inning", "batting_team", "bowling_team", "over", "ball", "batter",
                 "bowler", "non_striker", "batsman_runs", "extra_runs", "total_runs", "extras_type",
                 "is_wicket", "player_dismissed", "dismissal_kind"]
MATCH_COLS = ["id", "season", "season_year", "date", "venue", "city", "format", "team1", "team2",
              "toss_winner", "toss_decision", "winner"]


def init_db(path=DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    return conn


def load_kaggle(matches_csv, deliveries_csv, path=DB_PATH):
    conn = init_db(path)
    m = pd.read_csv(matches_csv).rename(columns={"Season": "season", "match_type": "format"})
    if "id" not in m.columns and "match_id" in m.columns:
        m = m.rename(columns={"match_id": "id"})
    m["season"] = m["season"].astype(str)
    m["season_year"] = m["season"].str[:4].astype(int)
    if "format" not in m.columns:
        m["format"] = "IPL"
    m["format"] = "IPL"  # Kaggle 'match_type' holds League/Final; normalise to competition
    m = m.reindex(columns=MATCH_COLS)
    d = pd.read_csv(deliveries_csv).rename(columns={"batsman": "batter", "inning": "inning"})
    d = d.reindex(columns=DELIVERY_COLS)
    m.to_sql("matches", conn, if_exists="append", index=False)
    d.to_sql("deliveries", conn, if_exists="append", index=False)
    bt = DATA_DIR / "bowler_types.csv"
    if bt.exists():
        pd.read_csv(bt).to_sql("bowler_types", conn, if_exists="append", index=False)
    conn.commit()
    return conn


def load_cricsheet(directory, path=DB_PATH):
    """Load Cricsheet JSON files from a directory into the SQLite schema."""
    conn = init_db(path)
    player_rows = {}
    files = sorted(Path(directory).rglob("*.json"))
    for file in files:
        data = json.loads(file.read_text(encoding="utf-8"))
        info = data["info"]
        match_id = int(hashlib.sha1(file.stem.encode()).hexdigest()[:12], 16) % 2147483647
        while conn.execute("SELECT 1 FROM matches WHERE id=?", (match_id,)).fetchone():
            match_id = (match_id + 1) % 2147483647
        teams = list(info["teams"])
        dates = info.get("dates", [])
        date = str(dates[0]) if dates else ""
        season = str(info.get("season", date[:4] or ""))
        try:
            season_year = int(season[:4])
        except ValueError:
            season_year = None
        toss = info.get("toss", {})
        outcome = info.get("outcome", {})
        winner = outcome.get("winner")
        conn.execute(
            "INSERT INTO matches VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (match_id, season, season_year, date, info.get("venue", ""),
             info.get("city", ""), info.get("match_type", "unknown"),
             teams[0], teams[1], toss.get("winner"), toss.get("decision"), winner),
        )
        for team, names in info.get("players", {}).items():
            for name in names:
                player_rows[name] = (name, team)
        for inning_no, innings in enumerate(data.get("innings", []), 1):
            team = innings.get("team", "")
            for over in innings.get("overs", []):
                for ball_no, delivery in enumerate(over.get("deliveries", []), 1):
                    runs = delivery.get("runs", {})
                    extras = delivery.get("extras", {})
                    wickets = delivery.get("wickets", [])
                    wicket = wickets[0] if wickets else {}
                    conn.execute(
                        "INSERT INTO deliveries VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (match_id, inning_no, team, teams[1] if team == teams[0] else teams[0],
                         over.get("over", 0), ball_no, delivery.get("batter", ""),
                         delivery.get("bowler", ""), delivery.get("non_striker", ""),
                         runs.get("batter", 0), runs.get("extras", 0), runs.get("total", 0),
                         next(iter(extras), None), int(bool(wickets)),
                         wicket.get("player_out"), wicket.get("kind")),
                    )
    conn.commit()
    conn.close()
    DATA_DIR.mkdir(exist_ok=True)
    with open(PLAYERS_CSV, "w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        writer.writerow(["player", "team", "role", "credits"])
        for name, team in sorted(player_rows.values()):
            writer.writerow([name, team, "BAT", 8.0])
    print(f"Loaded {len(files)} Cricsheet matches and {len(player_rows)} players into {path}.")
    return len(files)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="load SYNTHETIC demo data")
    ap.add_argument("--matches")
    ap.add_argument("--deliveries")
    ap.add_argument("--cricsheet-dir", help="directory containing Cricsheet JSON files")
    a = ap.parse_args()
    if a.demo:
        from .demo_data import build_demo
        build_demo()
    elif a.matches and a.deliveries:
        load_kaggle(a.matches, a.deliveries)
        print("Loaded Kaggle data into", DB_PATH)
    elif a.cricsheet_dir:
        load_cricsheet(a.cricsheet_dir)
    else:
        ap.error("use --demo, --matches/--deliveries, or --cricsheet-dir")
