from __future__ import annotations

import httpx

from config import SPORTSDB_BASE_URL


class SportsDBError(Exception):
    pass


async def _get(path: str, params: dict) -> dict:
    url = f"{SPORTSDB_BASE_URL}/{path}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json() or {}
    except httpx.HTTPError as exc:
        raise SportsDBError(f"Erreur réseau TheSportsDB : {exc}") from exc


async def search_team(name: str) -> list[dict]:
    data = await _get("searchteams.php", {"t": name})
    return data.get("teams") or []


async def team_last_events(team_id: str, n: int = 5) -> list[dict]:
    data = await _get("eventslast.php", {"id": team_id})
    events = data.get("results") or []
    return events[:n]


async def team_next_events(team_id: str, n: int = 5) -> list[dict]:
    data = await _get("eventsnext.php", {"id": team_id})
    events = data.get("events") or []
    return events[:n]


async def search_leagues(sport: str) -> list[dict]:
    data = await _get("search_all_leagues.php", {"s": sport})
    return data.get("countries") or []


async def league_next_events(league_id: str, n: int = 8) -> list[dict]:
    data = await _get("eventsnextleague.php", {"id": league_id})
    events = data.get("events") or []
    return events[:n]
