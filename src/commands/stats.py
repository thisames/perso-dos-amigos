import logging
import repos.firebase_repo as repo

from discord import Embed, User
from discord.bot import Bot
from discord.commands import ApplicationContext, Option, OptionChoice
from utils.embed import create_match_history_embed

logging.basicConfig(format='%(levelname)s %(name)s %(asctime)s: %(message)s', level=logging.INFO)
logger = logging.getLogger("c/stats")


def register_stats_commands(bot: Bot):
    @bot.slash_command(name="vitorias", description="Quantifica as vitorias de cada jogador")
    async def victories(
            ctx: ApplicationContext,
            mode: Option(int, "Escolha o modo de jogo", default=0,
                         choices=[OptionChoice("Todos", value=0), OptionChoice("5X5", value=5),
                                  OptionChoice("4X4", value=4), OptionChoice("3X3", value=3)]),
            season: Option(int, "Season", min_value=1, default=0)
    ):
        await ctx.response.defer(ephemeral=True)
        players = await repo.get_players()

        if season == 0:
            season_ref = await repo.get_last_season()
        else:
            season_ref = await repo.get_season_by_id(season)

        if season_ref is None:
            await ctx.followup.send("Season invalida")
            return

        matches = await repo.get_finished_matches(mode, season_ref)

        stats = {player.id: {"id": player.get("discord_id"), "wins": 0} for player in players}

        for match in matches:
            winning_team = match.get("blue_team") if match.get("result") == "BLUE" else match.get("red_team")

            for player_id in winning_team["players"]:
                stats[player_id]["wins"] += 1

        result_list = sorted(stats.items(), key=lambda x: x[1]["wins"], reverse=True)

        result_strings = [
            f"{rank + 1}º - <@{player['id']}> - {player['wins']} vitorias"
            for rank, (_, player) in enumerate(result_list)
        ]

        embed = Embed(
            title=f"Rankzudo {'Geral' if not mode else f'{mode}X{mode}'}",
            description="\n".join(result_strings)
        )

        await ctx.followup.send(embed=embed)

    @bot.slash_command(name="winrate", description="Quantifica o winrate de cada jogador")
    async def winrate(
            ctx: ApplicationContext,
            mode: Option(int, "Escolha o modo de jogo", name="modo", default=0,
                         choices=[OptionChoice("Todos", value=0), OptionChoice("5X5", value=5),
                                  OptionChoice("4X4", value=4), OptionChoice("3X3", value=3)]),
            minimal: Option(int, "Quantidade minima de jogos", name="corte", default=10, min_value=1, max_value=30),
            season: Option(int, "Season", min_value=1, default=0)
    ):
        await ctx.response.defer(ephemeral=True)
        players = await repo.get_players()

        if season == 0:
            season_ref = await repo.get_last_season()
        else:
            season_ref = await repo.get_season_by_id(season)

        if season_ref is None:
            await ctx.followup.send("Season invalida")
            return

        matches = await repo.get_finished_matches(mode, season_ref)

        stats = {player.id: {"id": player.get("discord_id"), "wins": 0, "losses": 0} for player in players}

        for match in matches:
            winning_team = match.get("blue_team") if match.get("result") == "BLUE" else match.get("red_team")
            losing_team = match.get("red_team") if match.get("result") == "BLUE" else match.get("blue_team")

            for player_id in winning_team["players"]:
                stats[player_id]["wins"] += 1

            for player_id in losing_team["players"]:
                stats[player_id]["losses"] += 1

        result_list = []
        for player_id, stat in stats.items():
            total_matches = stat["wins"] + stat["losses"]
            if total_matches >= minimal:
                result = (stat["wins"] / total_matches) * 100 if total_matches > 0 else 0
                result_list.append({"id": stat["id"], "winrate": result, "games": total_matches})

        result_list = sorted(result_list, key=lambda x: x["winrate"], reverse=True)

        result_strings = [
            f"{rank + 1}º - <@{player['id']}> - {player['winrate']:.2f}% | {player['games']} jogos"
            for rank, player in enumerate(result_list)
        ]

        embed = Embed(
            title=f"Rankzudo {'Geral' if not mode else f'{mode}X{mode}'} - Mínimo de {minimal} jogos",
            description="\n".join(result_strings)
        )

        await ctx.followup.send(embed=embed)

    @bot.slash_command(name="historico", description="Exibe o historico de partidas de um jogador")
    async def match_history(
            ctx: ApplicationContext,
            user: Option(User, "Usuário a ser consultado", name="usuário", required=False),
            limit: Option(int, "Limite de partidas", name="limite", default=10, min_value=1, max_value=50)
    ):
        await ctx.response.defer(ephemeral=True)
        player = await repo.get_player_by_discord_id(user.id if user else ctx.author.id)

        matches = await repo.get_matches_by_player(player.id, limit)

        embed = create_match_history_embed(matches, player)

        await ctx.followup.send(embed=embed)
