"""SYNTHETIC demo data so the whole system runs offline.

Player names are FICTIONAL and all numbers are simulated. Swap in Kaggle/Cricsheet data
for real analysis (see README).
"""
import csv
import random

from .config import DATA_DIR, DB_PATH, PLAYERS_CSV
from .db import init_db

CSK, MI = "Chennai Super Kings", "Mumbai Indians"
CHEPAUK = "MA Chidambaram Stadium, Chepauk"
WANKHEDE = "Wankhede Stadium"
HOME = {CSK: (CHEPAUK, "Chennai"), MI: (WANKHEDE, "Mumbai")}

# name, role, credits, bat skill, bowl skill, bowler type
SQUADS = {
    CSK: [("Arjun Menon", "WK", 9.0, .75, 0, ""), ("Karthik Iyer", "BAT", 9.5, .85, 0, ""),
          ("Rohan Deshpande", "BAT", 9.0, .80, 0, ""), ("Vikram Naidu", "BAT", 8.5, .70, 0, ""),
          ("Sameer Pillai", "AR", 9.0, .60, .60, "spin"), ("Dhruv Chauhan", "AR", 8.5, .55, .55, "pace"),
          ("Yash Rathore", "AR", 8.0, .50, .50, "pace"), ("Imran Sheikh", "BOWL", 8.5, .20, .80, "spin"),
          ("Tejas Kulkarni", "BOWL", 9.0, .20, .85, "pace"), ("Nikhil Joshi", "BOWL", 8.0, .20, .70, "pace"),
          ("Harsh Vardhan", "BOWL", 8.0, .20, .65, "spin"), ("Manoj Reddy", "BOWL", 7.5, .20, .60, "pace"),
          ("Ishaan Bose", "WK", 7.5, .55, 0, "")],
    MI: [("Aditya Nair", "WK", 9.5, .80, 0, ""), ("Siddharth Rao", "BAT", 10.0, .90, 0, ""),
         ("Kabir Malhotra", "BAT", 9.0, .80, 0, ""), ("Pranav Desai", "BAT", 8.5, .70, 0, ""),
         ("Neel Gupta", "AR", 9.5, .65, .60, "pace"), ("Ayaan Khan", "AR", 9.0, .60, .55, "spin"),
         ("Omkar Patil", "AR", 8.0, .50, .50, "pace"), ("Rahul Bhatt", "BOWL", 9.5, .20, .90, "pace"),
         ("Zaid Ansari", "BOWL", 8.5, .20, .75, "spin"), ("Kunal Mehra", "BOWL", 8.5, .20, .70, "pace"),
         ("Farhan Qureshi", "BOWL", 8.0, .20, .65, "spin"), ("Jay Solanki", "BOWL", 7.5, .20, .60, "pace"),
         ("Rishi Kapoor", "WK", 7.5, .55, 0, "")],
}

# Additional fictional squads make the offline demo useful for comparisons beyond
# CSK vs MI. Names, credits, and match numbers are synthetic.
TEAM_VENUES = {
    "Royal Challengers Bengaluru": ("M Chinnaswamy Stadium", "Bengaluru"),
    "Kolkata Knight Riders": ("Eden Gardens", "Kolkata"),
    "Delhi Capitals": ("Arun Jaitley Stadium", "Delhi"),
    "Sunrisers Hyderabad": ("Rajiv Gandhi International Stadium", "Hyderabad"),
    "Rajasthan Royals": ("Sawai Mansingh Stadium", "Jaipur"),
    "Punjab Kings": ("Maharaja Yadavindra Singh Stadium", "Mullanpur"),
    "Gujarat Titans": ("Narendra Modi Stadium", "Ahmedabad"),
    "Lucknow Super Giants": ("Bharat Ratna Shri Atal Bihari Vajpayee Ekana Stadium", "Lucknow"),
}
_GENERATED_TEAMS = {
    "Royal Challengers Bengaluru": "Bengaluru",
    "Kolkata Knight Riders": "Kolkata",
    "Delhi Capitals": "Delhi",
    "Sunrisers Hyderabad": "Hyderabad",
    "Rajasthan Royals": "Rajasthan",
    "Punjab Kings": "Punjab",
    "Gujarat Titans": "Gujarat",
    "Lucknow Super Giants": "Lucknow",
}
_ROLES = [("WK", 8.0, .62, 0, ""), ("BAT", 8.5, .78, 0, ""),
          ("BAT", 8.0, .72, 0, ""), ("BAT", 7.5, .66, 0, ""),
          ("AR", 8.5, .60, .58, "spin"), ("AR", 8.0, .56, .55, "pace"),
          ("AR", 7.5, .50, .50, "pace"), ("BOWL", 8.5, .20, .82, "pace"),
          ("BOWL", 8.0, .20, .76, "spin"), ("BOWL", 7.5, .20, .70, "pace"),
          ("BOWL", 7.5, .20, .66, "spin"), ("BOWL", 7.0, .20, .62, "pace"),
          ("WK", 7.0, .52, 0, "")]
for _team, _short in _GENERATED_TEAMS.items():
    SQUADS[_team] = [
        (f"{_short} Synthetic {i + 1}", role, credits, bat, bowl, kind)
        for i, (role, credits, bat, bowl, kind) in enumerate(_ROLES)
    ]
HOME.update(TEAM_VENUES)
ORDER = {"WK": 0, "BAT": 0, "AR": 1, "BOWL": 2}


def _innings(rng, bat_xi, bowl_xi, venue, target=None):
    """Yield delivery dicts for one innings (20 overs, 10 wickets, optional chase target)."""
    bat = sorted(bat_xi, key=lambda p: (ORDER[p[1]], -p[3]))
    bowlers = sorted([p for p in bowl_xi if p[4] >= .5], key=lambda p: -p[4])[:5]
    striker, non, nxt, wkts, total = 0, 1, 2, 0, 0
    for over in range(20):
        bw = bowlers[over % len(bowlers)]
        for ball in range(1, 7):
            b = bat[striker]
            spin_edge = (1.15 if bw[5] == "spin" else .95) if venue == CHEPAUK else (.95 if bw[5] == "spin" else 1.12)
            p_w = 0.042 * (0.5 + bw[4]) / (0.5 + b[3]) * spin_edge
            edge = (.6 + b[3]) * (1.3 - bw[4] * .5)
            w = [.42 * (1.2 - b[3]), .32, .06, .01, .075 * edge, .035 * edge]
            wicket = 1 if rng.random() < p_w else 0
            runs = 0 if wicket else rng.choices([0, 1, 2, 3, 4, 6], w)[0]
            kind = rng.choice(["bowled", "caught", "caught", "lbw", "run out"]) if wicket else None
            total += runs
            yield dict(inning=None, over=over, ball=ball, batter=b[0], bowler=bw[0],
                       non_striker=bat[non][0], batsman_runs=runs, extra_runs=0, total_runs=runs,
                       extras_type=None, is_wicket=wicket,
                       player_dismissed=b[0] if wicket else None, dismissal_kind=kind)
            if wicket:
                wkts += 1
                if wkts == 10 or nxt >= len(bat):
                    return
                striker, nxt = nxt, nxt + 1
            elif runs in (1, 3):
                striker, non = non, striker
            if target is not None and total >= target:
                return
        striker, non = non, striker


def build_demo(seed=42, seasons=(2023, 2024, 2025), path=DB_PATH):
    rng = random.Random(seed)
    conn = init_db(path)
    mid = 1000
    teams = list(SQUADS)
    pairings = [(teams[i], teams[(i + k) % len(teams)])
                for k in range(1, 3) for i in range(len(teams))]
    for yr in seasons:
        for k, (home, away) in enumerate(pairings):
            mid += 1
            venue, city = HOME[home]
            date = f"{yr}-{4 + k // 3:02d}-{(k * 3) % 27 + 1:02d}"
            toss = rng.choice([home, away])
            decision = rng.choices(["field", "bat"], [.65, .35])[0]
            first = toss if decision == "bat" else (away if toss == home else home)
            second = away if first == home else home
            xi = {t: rng.sample(SQUADS[t], 11) for t in (home, away)}
            for t in xi:  # need a keeper and 5 bowling options
                if not any(p[1] == "WK" for p in xi[t]):
                    xi[t][-1] = next(p for p in SQUADS[t] if p[1] == "WK")
            rows, scores = [], {}
            for inn, (bt, bl, tgt) in enumerate([(first, second, None), (second, first, None)], 1):
                if inn == 2:
                    tgt = scores[first] + 1
                inn_rows = list(_innings(rng, xi[bt], xi[bl], venue, tgt))
                scores[bt] = sum(r["total_runs"] for r in inn_rows)
                for r in inn_rows:
                    r.update(match_id=mid, inning=inn, batting_team=bt, bowling_team=bl)
                rows += inn_rows
            winner = first if scores[first] > scores[second] else (second if scores[second] > scores[first] else None)
            conn.execute("INSERT INTO matches VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                         (mid, str(yr), yr, date, venue, city, "T20", home, away, toss, decision, winner))
            cols = ["match_id", "inning", "batting_team", "bowling_team", "over", "ball", "batter",
                    "bowler", "non_striker", "batsman_runs", "extra_runs", "total_runs", "extras_type",
                    "is_wicket", "player_dismissed", "dismissal_kind"]
            conn.executemany(f"INSERT INTO deliveries VALUES({','.join('?' * len(cols))})",
                             [tuple(r[c] for c in cols) for r in rows])
    bts = {p[0]: p[5] for sq in SQUADS.values() for p in sq if p[5]}
    conn.executemany("INSERT INTO bowler_types VALUES(?,?)", bts.items())
    conn.commit()
    conn.close()
    DATA_DIR.mkdir(exist_ok=True)
    with open(PLAYERS_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["player", "team", "role", "credits"])
        for t, sq in SQUADS.items():
            for p in sq:
                w.writerow([p[0], t, p[1], p[2]])
    print(f"Synthetic demo DB written to {path} ({mid - 1000} matches). NAMES AND NUMBERS ARE FICTIONAL.")
