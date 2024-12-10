import discord
import os
import io

import repos.firebase_repo as repo
from discord_model.view import TeamSelectView, DeleteButtons, ResultButtons
from discord import Option, OptionChoice

from repos.champions_repo import ImageDict
from team_generator.generator import generate_team
from dotenv import load_dotenv
from PIL import Image

load_dotenv()
bot = discord.Bot()
data = ImageDict()


@bot.event
async def on_ready():
    print(f"{bot.user} tá on pai!")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.custom,
            name="custom",
            state="Fraudando as runas...."
        )
    )


@bot.slash_command(name="adicionar", description="Adiciona jogadores a lista de ativos")
async def adicionar(
        ctx: discord.ApplicationContext,
        fixed: Option(int, "Os times serão fixos", name="fixos", default=False,
                      choices=[OptionChoice("Sim", value=True), OptionChoice("Não", value=False)])):
    if await block_trolls(ctx):
        await ctx.response.defer(ephemeral=True)
        if fixed:
            repo.set_config("fixed_teams", True)
            await ctx.followup.send("Monte os times!", view=TeamSelectView(["A", "B"]))
        else:
            if repo.get_config("fixed_teams"):
                await ctx.followup.send("Modo de times fixos, caso queira alterar use o /limpar!")
                return

            await ctx.followup.send("Monta o time!", view=TeamSelectView())


@bot.slash_command(name="limpar", description="Apaga todos os jogadores da lista de ativos")
async def limpar(ctx):
    if await block_trolls(ctx):
        await ctx.response.defer(ephemeral=True)
        repo.clear_active_players()
        await ctx.followup.send("A lista de jogadores ativos foi esvaziada!")


@bot.slash_command(name="ativos", description="Mostra os jogadores ativos")
async def ativos(ctx):
    if await block_trolls(ctx):
        await ctx.response.defer()
        players = repo.get_active_players()

        if repo.get_config("fixed_teams"):
            embed = discord.Embed(
                title="Times montados",
                color=discord.Colour.blurple(),
            )

            team = ""
            for idx, player in enumerate(players.get("A")):
                player_info = repo.get_player_by_id(player)
                team += f"{idx + 1} - <@{player_info.get('discord_id')}>\n"

            embed.add_field(name=f"Time A", value=team, inline=True)

            team = ""
            for idx, player in enumerate(players.get("B")):
                player_info = repo.get_player_by_id(player)
                team += f"{idx + 1} - <@{player_info.get('discord_id')}>\n"

            embed.add_field(name=f"Time B", value=team, inline=True)

            await ctx.followup.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Jogadores ativos",
                color=discord.Colour.blurple(),
            )

            for idx, player in enumerate(players):
                player_info = repo.get_player_by_id(player)
                embed.add_field(name=f"Jogador {idx + 1}", value=f"<@{player_info.get('discord_id')}>", inline=True)

            await ctx.followup.send(embed=embed, view=DeleteButtons(players))


async def send_embed(player_info, embed):
    player_discord = await bot.fetch_user(player_info.get("discord_id"))

    embed["file"].seek(0)
    file = discord.File(fp=embed["file"], filename="image.png")

    try:
        await player_discord.send(file=file, embed=embed["embed"])
    except discord.Forbidden:
        print(f"Failed to send message to user {player_discord.name}")


@bot.slash_command(name="sortear", description="Sortea os times e campeões")
async def sortear(ctx):
    if await block_trolls(ctx):
        await ctx.response.defer()
        players = repo.get_active_players()
        result = generate_team(players, list(data), repo.get_config("fixed_teams"))
        match_id = repo.store_match(result)

        blue_embed = generate_embed(result.get("blue_team").get("champions"), discord.Colour.blue())
        red_embed = generate_embed(result.get("red_team").get("champions"), discord.Colour.red())

        blue_team_players = ""
        for idx, player in enumerate(result.get("blue_team").get("players")):
            player_info = repo.get_player_by_id(player)
            await send_embed(player_info, blue_embed)
            blue_team_players += f"{idx + 1} - <@{player_info.get('discord_id')}>\n"

        red_team_players = ""
        for idx, player in enumerate(result.get("red_team").get("players")):
            player_info = repo.get_player_by_id(player)
            await send_embed(player_info, red_embed)
            red_team_players += f"{idx + 1} - <@{player_info.get('discord_id')}>\n"

        embed = discord.Embed(
            title="Partidazuda",
            description="Em um embate do bem contra o mal, quem vencerá?",
            color=discord.Colour.blurple(),
        )
        embed.add_field(name="Time azul (Lado esquerdo)", value=blue_team_players)
        embed.add_field(name="Time vermelho (Lado direito)", value=red_team_players)
        await ctx.followup.send(embed=embed, view=ResultButtons(match_id, ctx.author.id))


@bot.slash_command(name="registrar", description="Adicionar jogador")
async def registrar(ctx, nome: str, user: discord.User):
    if await block_trolls(ctx):
        await ctx.response.defer(ephemeral=True)
        repo.set_player(nome, user)
        await ctx.followup.send(f"{nome} registrado com sucesso.")


@bot.slash_command(name="vitorias", description="Quantifica as vitorias de cada jogador")
async def vitorias(
        ctx: discord.ApplicationContext,
        mode: Option(int, "Escolha o modo de jogo", default=0,
                     choices=[OptionChoice("Todos", value=0), OptionChoice("5X5", value=5),
                              OptionChoice("4X4", value=4), OptionChoice("3X3", value=3)])):
    if await block_trolls(ctx):
        await ctx.response.defer()
        players = repo.get_players()
        matches = repo.get_finished_matches(mode)

        stats = {player.id: {"id": player.get("discord_id"), "wins": 0} for player in players}

        for match in matches:
            winning_team = match.get("blue_team") if match.get("result") == "BLUE" else match.get("red_team")

            for player_id in winning_team["players"]:
                stats[player_id]["wins"] += 1

        result_list = sorted(stats.items(), key=lambda x: x["wins"], reverse=True)

        result_strings = [
            f"{rank + 1}º - <@{player['id']}> - {player['wins']} vitorias"
            for rank, player in enumerate(result_list)
        ]

        embed = discord.Embed(
            title=f"Rankzudo {'Geral' if not mode else f'{mode}X{mode}'}",
            description="\n".join(result_strings)
        )

        await ctx.followup.send(embed=embed)


@bot.slash_command(name="winrate", description="Quantifica o winrate de cada jogador")
async def winrate(
        ctx: discord.ApplicationContext,
        mode: Option(int, "Escolha o modo de jogo", name="modo", default=0,
                     choices=[OptionChoice("Todos", value=0), OptionChoice("5X5", value=5),
                              OptionChoice("4X4", value=4), OptionChoice("3X3", value=3)]),
        minimal: Option(int, "Quantidade minima de jogos", name="corte", default=10, min_value=1, max_value=30)):
    if await block_trolls(ctx):
        await ctx.response.defer()
        players = repo.get_players()
        matches = repo.get_finished_matches(mode)

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

        embed = discord.Embed(
            title=f"Rankzudo {'Geral' if not mode else f'{mode}X{mode}'} - Mínimo de {minimal} jogos",
            description="\n".join(result_strings)
        )

        await ctx.followup.send(embed=embed)


def generate_embed(champions_list, colour):
    champion_string = ""

    max_width, max_height = 680, 281

    new_im = Image.new('RGBA', (max_width, max_height), (255, 0, 0, 0))

    x_offset = 10
    y_offset = 10
    for champion in champions_list:
        champion_data = data[champion]
        champion_string += f"{champion_data['name']}\n"
        img = Image.open(io.BytesIO(champion_data["image"]))
        new_im.paste(img, (x_offset, y_offset))

        x_offset += 133
        if x_offset >= max_width - 10:
            x_offset = 10
            y_offset += 133

    embed = discord.Embed(
        title="Só os bonecudos",
        description=champion_string,
        color=colour,
    )

    image_buffer = io.BytesIO()
    new_im.save(image_buffer, format='PNG')

    embed.set_image(url="attachment://image.png")
    return {"embed": embed, "file": image_buffer}


async def block_trolls(ctx):
    if ctx.author.id == 270966282461904896:
        embed = discord.Embed(
            title="Só a cabecinha kkkkkkkkkkkkkkkkkkkk",
        )

        embed.set_image(url="https://pbs.twimg.com/media/GWQtIvhWoAA-KV0?format=jpg&name=900x900")

        await ctx.respond(embed=embed, ephemeral=True)

    return ctx.author.id != 270966282461904896


def main():
    bot.run(os.getenv("TOKEN"))


if __name__ == "__main__":
    main()
