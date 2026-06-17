from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import SPORT_ALIASES, SPORT_EMOJIS, TELEGRAM_BOT_TOKEN
from sportsdb_api import (
    SportsDBError,
    league_next_events,
    search_leagues,
    search_team,
    team_last_events,
    team_next_events,
)
from analysis import compute_form, predict_match

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def resolve_sport(raw: str) -> str | None:
    return SPORT_ALIASES.get(raw.lower())


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Salut ! Je suis ton bot d'analyse sportive ⚽🏀🏏🎾\n\n"
        "Tape /aide pour voir toutes les commandes disponibles."
    )


async def aide(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📋 Commandes disponibles :\n\n"
        "/equipe <sport> <nom> — infos + prochain match\n"
        "  ex: /equipe foot Marseille\n\n"
        "/forme <sport> <nom> — 5 derniers résultats\n"
        "  ex: /forme basket Lakers\n\n"
        "/pronostic <sport> <équipe A> vs <équipe B>\n"
        "  ex: /pronostic foot Lyon vs Marseille\n\n"
        "/tennis <nom du tournoi> — prochains matchs\n"
        "  ex: /tennis Roland Garros\n\n"
        "Sports reconnus : foot, basket, cricket, tennis"
    )


async def equipe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "Utilisation : /equipe <sport> <nom de l'équipe>\n"
            "ex: /equipe foot Marseille"
        )
        return

    sport = resolve_sport(args[0])
    if sport is None or sport == "Tennis":
        await update.message.reply_text(
            "Sport non reconnu pour cette commande. Utilise : foot, basket, cricket.\n"
            "(Pour le tennis, utilise /tennis <tournoi>)"
        )
        return

    team_name = " ".join(args[1:])
    emoji = SPORT_EMOJIS.get(sport, "🏆")

    try:
        teams = await search_team(team_name)
    except SportsDBError:
        await update.message.reply_text("⚠️ Impossible de contacter la base de données sportive.")
        return

    teams = [t for t in teams if t.get("strSport") == sport]
    if not teams:
        await update.message.reply_text(f"Aucune équipe {sport} trouvée pour « {team_name} ».")
        return

    team = teams[0]
    team_id = team["idTeam"]

    try:
        next_events = await team_next_events(team_id, n=1)
    except SportsDBError:
        next_events = []

    lines = [f"{emoji} {team.get('strTeam')}"]
    if team.get("strLeague"):
        lines.append(f"Compétition : {team['strLeague']}")
    if team.get("strStadium"):
        lines.append(f"Stade : {team['strStadium']}")

    if next_events:
        ev = next_events[0]
        lines.append(
            f"\n📅 Prochain match : {ev.get('strHomeTeam')} vs "
            f"{ev.get('strAwayTeam')} le {ev.get('dateEvent')}"
        )
    else:
        lines.append("\n📅 Pas de prochain match programmé trouvé.")

    await update.message.reply_text("\n".join(lines))


async def forme(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "Utilisation : /forme <sport> <nom de l'équipe>\nex: /forme basket Lakers"
        )
        return

    sport = resolve_sport(args[0])
    if sport is None or sport == "Tennis":
        await update.message.reply_text(
            "Sport non reconnu pour cette commande. Utilise : foot, basket, cricket."
        )
        return

    team_name = " ".join(args[1:])
    emoji = SPORT_EMOJIS.get(sport, "🏆")

    try:
        teams = await search_team(team_name)
    except SportsDBError:
        await update.message.reply_text("⚠️ Impossible de contacter la base de données sportive.")
        return

    teams = [t for t in teams if t.get("strSport") == sport]
    if not teams:
        await update.message.reply_text(f"Aucune équipe {sport} trouvée pour « {team_name} ».")
        return

    team = teams[0]
    team_id = team["idTeam"]

    try:
        events = await team_last_events(team_id, n=5)
    except SportsDBError:
        await update.message.reply_text("⚠️ Impossible de récupérer les résultats récents.")
        return

    form = compute_form(events, team_id)
    if form["played"] == 0:
        await update.message.reply_text(f"{emoji} Pas de résultats récents disponibles pour {team['strTeam']}.")
        return

    await update.message.reply_text(
        f"{emoji} Forme de {team['strTeam']} (5 derniers matchs) :\n"
        f"{' '.join(form['results'])}\n"
        f"Victoires: {form['wins']} | Nuls: {form['draws']} | Défaites: {form['losses']}\n"
        f"Score de forme : {form['score']}/100"
    )


async def pronostic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if len(args) < 4 or "vs" not in [a.lower() for a in args]:
        await update.message.reply_text(
            "Utilisation : /pronostic <sport> <équipe A> vs <équipe B>\n"
            "ex: /pronostic foot Lyon vs Marseille"
        )
        return

    sport = resolve_sport(args[0])
    if sport is None or sport == "Tennis":
        await update.message.reply_text(
            "Sport non reconnu pour cette commande. Utilise : foot, basket, cricket."
        )
        return

    rest = args[1:]
    lower_rest = [a.lower() for a in rest]
    vs_index = lower_rest.index("vs")
    name_a = " ".join(rest[:vs_index])
    name_b = " ".join(rest[vs_index + 1 :])

    if not name_a or not name_b:
        await update.message.reply_text("Merci de préciser deux équipes séparées par 'vs'.")
        return

    try:
        teams_a = [t for t in await search_team(name_a) if t.get("strSport") == sport]
        teams_b = [t for t in await search_team(name_b) if t.get("strSport") == sport]
    except SportsDBError:
        await update.message.reply_text("⚠️ Impossible de contacter la base de données sportive.")
        return

    if not teams_a or not teams_b:
        missing = name_a if not teams_a else name_b
        await update.message.reply_text(f"Équipe introuvable : « {missing} ».")
        return

    team_a, team_b = teams_a[0], teams_b[0]

    try:
        events_a = await team_last_events(team_a["idTeam"], n=5)
        events_b = await team_last_events(team_b["idTeam"], n=5)
    except SportsDBError:
        await update.message.reply_text("⚠️ Impossible de récupérer les résultats récents.")
        return

    form_a = compute_form(events_a, team_a["idTeam"])
    form_b = compute_form(events_b, team_b["idTeam"])

    message = predict_match(form_a, form_b, team_a["strTeam"], team_b["strTeam"])
    await update.message.reply_text(message)


async def tennis(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args:
        await update.message.reply_text(
            "Utilisation : /tennis <nom du tournoi>\nex: /tennis Roland Garros"
        )
        return

    tournament_name = " ".join(args).lower()

    try:
        leagues = await search_leagues("Tennis")
    except SportsDBError:
        await update.message.reply_text("⚠️ Impossible de contacter la base de données sportive.")
        return

    matches = [
        lg for lg in leagues if tournament_name in (lg.get("strLeague") or "").lower()
    ]
    if not matches:
        await update.message.reply_text(
            f"Aucun tournoi trouvé pour « {tournament_name} ». "
            "Essaie un nom plus général (ex: ATP, WTA)."
        )
        return

    league = matches[0]
    try:
        events = await league_next_events(league["idLeague"], n=8)
    except SportsDBError:
        await update.message.reply_text("⚠️ Impossible de récupérer les prochains matchs.")
        return

    if not events:
        await update.message.reply_text(
            f"🎾 {league.get('strLeague')} : aucun match à venir trouvé pour le moment."
        )
        return

    lines = [f"🎾 {league.get('strLeague')} — prochains matchs :"]
    for ev in events:
        lines.append(f"• {ev.get('strHomeTeam')} vs {ev.get('strAwayTeam')} ({ev.get('dateEvent')})")

    await update.message.reply_text("\n".join(lines))


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN manquant. Ajoute-le dans les Secrets de Replit."
        )

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("aide", aide))
    application.add_handler(CommandHandler("equipe", equipe))
    application.add_handler(CommandHandler("forme", forme))
    application.add_handler(CommandHandler("pronostic", pronostic))
    application.add_handler(CommandHandler("tennis", tennis))

    logger.info("Bot démarré, en attente de messages...")
    application.run_polling()


if __name__ == "__main__":
    main()
