import discord
import os
import io

import src.repos.firebase_repo as repo
from src.discord_model.view import TeamSelectView, DeleteButtons, ResultButtons

from src.repos.champions_repo import ImageDict
from src.team_generator.generator import generate_team
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
            state="Fraudando as urnas...."
        )
    )


@bot.slash_command(name="adicionar", description="Adiciona jogadores a lista de ativos")
async def adicionar(ctx):
    if await block_trolls(ctx):
        try:
            await ctx.response.defer()
            await ctx.followup.send("Monta o time!", view=TeamSelectView(), ephemeral=True)
        except Exception as e:
            print(repr(e))


@bot.slash_command(name="limpar", description="Apaga todos os jogadores da lista de ativos")
async def limpar(ctx):
    if await block_trolls(ctx):
        try:
            await ctx.response.defer()
            repo.clear_active_players()
            await ctx.followup.send("A lista de jogadores ativos foi esvaziada!")
        except Exception as e:
            print(repr(e))


@bot.slash_command(name="ativos", description="Mostra os jogadores ativos")
async def ativos(ctx):
    if await block_trolls(ctx):
        try:
            await ctx.response.defer()
            players = repo.get_active_players()

            embed = discord.Embed(
                title="Jogadores ativos",
                color=discord.Colour.blurple(),
            )

            for idx, player in enumerate(players):
                player_info = repo.get_player_by_id(player)
                embed.add_field(name=f"Jogador {idx + 1}", value=f"<@{player_info.get('discord_id')}>", inline=True)

            await ctx.followup.send(embed=embed, view=DeleteButtons(players))
        except Exception as e:
            print(repr(e))


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
        result = generate_team(players, list(data))
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
        try:
            await ctx.response.defer()
            repo.set_player(nome, user)
            await ctx.followup.send(f"{nome} registrado com sucesso.", ephemeral=True)
        except Exception as e:
            print(repr(e))


@bot.slash_command(name="vitorias", description="Quantifica as vitorias de cada jogador")
async def vitorias(ctx):
    if await block_trolls(ctx):
        await ctx.response.defer()
        players = repo.get_players()
        matches = repo.get_finished_matches()

        player_map = {}
        for player in players:
            player_map[player.id] = player

        victory_count = {}

        for match in matches:
            if match.get("result") == "BLUE":
                winners = match.get("blue_team")["players"]
            else:
                winners = match.get("red_team")["players"]

            for player in winners:
                if player not in victory_count:
                    victory_count[player] = 0

                victory_count[player] += 1

        victory_count = dict(sorted(victory_count.items(), key=lambda item: item[1], reverse=True))

        result = ""
        for idx, player in enumerate(victory_count.items()):
            result += f"{idx + 1}º <@{player_map.get(player[0]).get('discord_id')}> - {player[1]} vitorias\n"

        embed = discord.Embed(
            title="Rankzudo",
            description=result
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
