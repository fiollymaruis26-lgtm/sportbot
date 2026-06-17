from __future__ import annotations


def _result_for_team(event: dict, team_id: str) -> str:
    home_id = event.get("idHomeTeam")
    home_score_raw = event.get("intHomeScore")
    away_score_raw = event.get("intAwayScore")

    if home_score_raw is None or away_score_raw is None:
        return "?"

    try:
        home_score = int(home_score_raw)
        away_score = int(away_score_raw)
    except (TypeError, ValueError):
        return "?"

    if home_score == away_score:
        return "D"

    is_home = str(home_id) == str(team_id)
    team_won = (is_home and home_score > away_score) or (
        not is_home and away_score > home_score
    )
    return "W" if team_won else "L"


def compute_form(events: list[dict], team_id: str) -> dict:
    results = [_result_for_team(e, team_id) for e in events]
    results = [r for r in results if r != "?"]

    wins = results.count("W")
    draws = results.count("D")
    losses = results.count("L")
    total = len(results) or 1

    score = (wins * 3 + draws * 1) / (total * 3) * 100

    return {
        "results": results,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "played": len(results),
        "score": round(score, 1),
    }


def predict_match(form_a: dict, form_b: dict, name_a: str, name_b: str) -> str:
    if form_a["played"] == 0 and form_b["played"] == 0:
        return (
            "❌ Pas assez de données récentes pour les deux équipes "
            "pour proposer une estimation."
        )

    score_a = form_a["score"]
    score_b = form_b["score"]
    total = (score_a + score_b) or 1

    prob_a = round(score_a / total * 100)
    prob_b = 100 - prob_a

    return (
        f"📊 Estimation basée sur la forme des {form_a['played']}/{form_b['played']} "
        f"derniers matchs disponibles :\n\n"
        f"{name_a} : {prob_a}% ({''.join(form_a['results']) or 'N/A'})\n"
        f"{name_b} : {prob_b}% ({''.join(form_b['results']) or 'N/A'})\n\n"
        f"⚠️ Estimation statistique simple à titre informatif, sans prise en "
        f"compte des blessures, calendrier, etc. Ce n'est pas un conseil de pari."
    )
