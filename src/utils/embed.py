import io
import discord

from PIL import Image
from src.repos.champions_repo import ImageDict


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
