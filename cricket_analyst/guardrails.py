"""Guardrails: betting refusal, news-freshness flags, mandatory disclaimer."""
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from .config import NEWS_MAX_AGE_HOURS

BETTING_RE = re.compile(
    r"\b(bet|bets|betting|wager|wagering|gambl\w*|bookie|bookmaker|sure[- ]?shot|"
    r"real[- ]money|odds to win|stake money)\b", re.I)

REFUSAL = ("I can't help with betting or wagering real money. I'm happy to help with "
           "match analysis, rules explanations, or a free-to-play fantasy team instead.")

DISCLAIMER = ("_Projections are statistical estimates, not certainties: cricket is high-variance "
              "and team news can change before the toss. This is for entertainment and analysis; "
              "it is not betting advice and does not support real-money wagering._")

OUT_OF_SCOPE = (
    "I'm a cricket match analyst, so I can answer questions about cricket rules, "
    "statistics, team news, and fantasy teams. I can't provide general information "
    "about colleges or other non-cricket topics."
)

_NON_CRICKET_RE = re.compile(
    r"^\s*(hi|hello|hey|good morning|good afternoon|good evening)\s*[!.?]*$|"
    r"\b(college|university|school|admission|course|degree|engineering college)\b",
    re.I,
)


def is_betting_request(query: str) -> bool:
    return bool(BETTING_RE.search(query))


def is_obviously_out_of_scope(query: str) -> bool:
    return bool(_NON_CRICKET_RE.search(query))


def _parse_dt(s):
    if not s:
        return None
    for fn in (parsedate_to_datetime, lambda x: datetime.fromisoformat(x.replace("Z", "+00:00"))):
        try:
            dt = fn(s)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return None


def assess_freshness(results, now=None, max_age_hours=NEWS_MAX_AGE_HOURS):
    """Annotate each search result with age_hours and summarise freshness.

    Items with no parsable date count as 'unknown' (unverified, never treated as fresh).
    """
    now = now or datetime.now(timezone.utc)
    items, ages = [], []
    for r in results:
        dt = _parse_dt(r.get("published_date"))
        age = None if dt is None else (now - dt).total_seconds() / 3600
        if age is not None:
            ages.append(age)
        items.append({**r, "age_hours": age, "stale": age is None or age > max_age_hours})
    fresh = sum(1 for i in items if not i["stale"])
    newest = min(ages) if ages else None
    warning = None
    if not fresh:
        warning = ("⚠️ No news from the last 24 hours was found"
                   + (f" (newest is ~{newest:.0f}h old)" if newest is not None
                      else " (sources carry no dates)")
                   + ". Check official team channels before the toss.")
    return {"items": items, "fresh_count": fresh,
            "unknown_date_count": sum(1 for i in items if i["age_hours"] is None),
            "newest_age_hours": newest, "stale": fresh == 0, "warning": warning}
