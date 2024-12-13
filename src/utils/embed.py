import io
from datetime import datetime

import discord

from PIL import Image
from repos.champions_repo import ImageDict


def create_image_from_champions(champions_list: list[str], data: ImageDict) -> io.BytesIO:
    max_width, max_height = 680, 281
    new_im = Image.new('RGBA', (max_width, max_height), (255, 0, 0, 0))

    x_offset = 10
    y_offset = 10
    for champion in champions_list:
        champion_data = data[champion]
        img = Image.open(io.BytesIO(champion_data["image"]))
        new_im.paste(img, (x_offset, y_offset))

        x_offset += 133
        if x_offset >= max_width - 10:
            x_offset = 10
            y_offset += 133

    image_buffer = io.BytesIO()
    new_im.save(image_buffer, format='PNG')
    image_buffer.seek(0)
    return image_buffer


def create_champion_embed(champions_list: list[str], data: ImageDict, colour: discord.Colour) -> dict:
    champion_string = "\n".join([data[champ]["name"] for champ in champions_list])

    image_buffer = create_image_from_champions(champions_list, data)
    embed = discord.Embed(
        title="Só os bonecudos",
        description=champion_string,
        color=colour,
    )
    embed.set_image(url="attachment://image.png")

    return {"embed": embed, "file": image_buffer}


def create_active_players_embed(players):
    """
    Create an embed displaying the list of active players.
    """
    embed = discord.Embed(title="Jogadores ativos", color=discord.Colour.blurple())

    for idx, player in enumerate(players):
        embed.add_field(
            name=f"Jogador {idx + 1}",
            value=f"<@{player.get('discord_id')}>",
            inline=True,
        )
    return embed


def create_active_team_embed(players):
    """
    Create an embed displaying the list of active players.
    """
    embed = discord.Embed(title="Times montados", color=discord.Colour.blurple())

    team = ""
    for idx, player in enumerate(players.get("A")):
        team += f"{idx + 1} - <@{player.get('discord_id')}>\n"

    embed.add_field(name=f"Time A", value=team, inline=True)

    team = ""
    for idx, player in enumerate(players.get("B")):
        team += f"{idx + 1} - <@{player.get('discord_id')}>\n"

    embed.add_field(name=f"Time B", value=team, inline=True)
    return embed


def create_match_history_embed(matches, player):
    """
    Create an embed displaying the last matches of player.
    """
    embed = discord.Embed(title=f"Últimas Partidas de {player.get('nome')}", color=discord.Colour.blurple())

    if not matches:
        embed.description = "Este jogador não possui partidas finalizadas."
        return embed

    for match in matches:
        match_date = match.get("timestamp")
        mode = match.get("mode")
        winner_team = (
            match.get("blue_team")["players"]
            if match.get("result") == "BLUE" else
            match.get("red_team")["players"]
        )
        result = player.id in winner_team

        if isinstance(match_date, datetime):
            match_date = match_date.strftime("%d/%m/%Y %H:%M")

        embed.add_field(
            name=f"{match_date} - {mode}X{mode}",
            value=("Vitória" if result else "Derrota"),
            inline=False
        )
    return embed
