import random
from datetime import datetime, timedelta, timezone

import pytest

from cricket_analyst import guardrails, stats
from cricket_analyst.config import DB_PATH, FantasyRules
from cricket_analyst.team_builder import Player, build_team, pick_leaders, project, violations

RULES = FantasyRules()


@pytest.fixture(scope="module", autouse=True)
def demo_db():
    from cricket_analyst.demo_data import build_demo
    build_demo()


def test_player_stats_filters():
    d = stats.player_stats("Karthik Iyer", venue="Chepauk", season_from=2024, season_to=2025)
    assert d["batting"]["innings"] > 0 and d["fantasy"]["matches"] > 0
    assert stats.player_stats("Nobody Real")["error"]


def test_venue_and_h2h():
    v = stats.venue_stats("Chepauk")
    assert v["avg_first_innings"] > 100 and set(v["wickets_pace_spin_pct"]) == {"pace", "spin"}
    h = stats.head_to_head("team", "CSK", "MI")
    assert sum(h["wins"].values()) == h["matches"]


def _pool(seed):
    from cricket_analyst.team_builder import load_pool
    rng = random.Random(seed)
    return [Player(p.name, p.team, p.role, p.credits, round(rng.uniform(15, 80), 1)) for p in load_pool()]


@pytest.mark.parametrize("seed", range(20))
def test_builder_validator_loop_converges(seed):
    pool, sel = _pool(seed), None
    for i in range(12):
        sel = build_team(pool, RULES, sel)
        if not violations(sel, RULES):
            break
    assert violations(sel, RULES) == [], (seed, violations(sel, RULES))
    c, vc = pick_leaders(sel)
    assert c != vc


def test_validator_catches_each_constraint():
    pool = _pool(1)
    csk = [p for p in pool if p.team.startswith("Chennai")][:8]
    assert any(v.startswith("SIZE") for v in violations(csk, RULES))
    assert any(v.startswith("TEAM_CAP") for v in violations(csk, RULES))
    rich = [Player(f"x{i}", "A" if i % 2 else "B", "BAT", 15) for i in range(11)]
    assert any(v.startswith("BUDGET") for v in violations(rich, RULES))
    assert any(v.startswith("ROLE_MAX") for v in violations(rich, RULES))


def test_projection_blend():
    assert project(None, None)[0] == 20.0
    assert project(40, 60, 50, 5)[0] == pytest.approx(0.5 * 60 + 0.3 * 40 + 0.2 * 50)


def test_freshness_flags():
    now = datetime(2026, 9, 29, 12, tzinfo=timezone.utc)
    fmt = lambda h: (now - timedelta(hours=h)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    ok = guardrails.assess_freshness([{"published_date": fmt(3)}, {"published_date": fmt(50)}], now)
    assert not ok["stale"] and ok["fresh_count"] == 1
    old = guardrails.assess_freshness([{"published_date": fmt(30)}, {}], now)
    assert old["stale"] and "24 hours" in old["warning"] and old["unknown_date_count"] == 1


def test_betting_guardrail():
    assert guardrails.is_betting_request("which team should I bet on tonight?")
    assert not guardrails.is_betting_request("Build me a fantasy XI for CSK vs MI within 100 credits")


def test_graph_builds_langchain_toolset():
    from cricket_analyst.graph import build_toolset

    tool_names = [tool.name for tool in build_toolset([])]
    assert "resolve_player_name" in tool_names
    assert "rules_search" in tool_names
    assert "team_snapshot" in tool_names


def test_evaluation_set_and_logging_setup():
    from cricket_analyst.evaluation import load_eval_set
    from cricket_analyst.observability import logger, setup_logging

    items = load_eval_set()
    assert len(items) >= 3
    assert all("query" in item for item in items)
    assert logger.name == "cricket_analyst"
    assert setup_logging() is logger
