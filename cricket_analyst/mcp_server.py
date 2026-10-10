"""MCP server exposing player_stats, head_to_head, venue_stats over stdio.
Run standalone: python -m cricket_analyst.mcp_server
"""
from typing import Optional

from mcp.server.fastmcp import FastMCP

from . import stats

mcp = FastMCP("cricket-stats")


@mcp.tool()
def player_stats(player: str, discipline: str = "all", season_from: Optional[int] = None,
                 season_to: Optional[int] = None, venue: Optional[str] = None,
                 format: Optional[str] = None) -> dict:
    """Batting/bowling aggregates and fantasy-point form for a player.
    discipline: 'batting' | 'bowling' | 'all' (all also returns fantasy points and last-10 form).
    season_from/season_to: inclusive years, e.g. 2023..2025. venue: substring, e.g. 'Chepauk'.
    format: e.g. 'T20' or 'IPL'."""
    return stats.player_stats(player, discipline, season_from, season_to, venue, format)


@mcp.tool()
def head_to_head(kind: str, a: str, b: str, season_from: Optional[int] = None,
                 season_to: Optional[int] = None, venue: Optional[str] = None) -> dict:
    """Team-vs-team (kind='team', e.g. a='CSK', b='MI') or batter-vs-bowler
    (kind='batter_vs_bowler', a=batter, b=bowler) records."""
    return stats.head_to_head(kind, a, b, season_from, season_to, venue)


@mcp.tool()
def venue_stats(venue: str, season_from: Optional[int] = None, season_to: Optional[int] = None,
                format: Optional[str] = None) -> dict:
    """Average 1st/2nd innings scores, pace/spin wicket split and toss outcomes for a venue."""
    return stats.venue_stats(venue, season_from, season_to, format)


if __name__ == "__main__":
    mcp.run(transport="stdio")
