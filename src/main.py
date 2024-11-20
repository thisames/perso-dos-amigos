import math

import discord
from imageio.v2 import imread
import os
import repo
import io

from team_generator.generator import generate_team
from dotenv import load_dotenv
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import ImageGrid

load_dotenv()
bot = discord.Bot()


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


class TeamSelect(discord.ui.Select):
    async def callback(self, interaction: discord.Interaction):
        repo.add_active_players(self.values)

        await interaction.message.edit("Os jogadores foram adicionados a lista de ativos.", view=None)


class TeamSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        players = repo.get_players()
        players_options = []
        for player in players:
            players_options.append(discord.SelectOption(label=player.get("nome"), value=player.id))

        select = TeamSelect(
            placeholder="Escolha os jogadores ativos!",
            min_values=1,
            max_values=repo.get_players_max_size(),
            options=players_options
        )

        self.add_item(select)


class DeleteButton(discord.ui.Button):
    async def callback(self, interaction: discord.Interaction):
        player_id = self.custom_id
        repo.remove_active_player(player_id)

        # Isso aqui tá feio demais kkkkkkkkkkkkkkkkkkkkkkkkkkk
        players = repo.get_active_players()

        embed = discord.Embed(
            title="Jogadores ativos",
            color=discord.Colour.blurple(),
        )

        for idx, player in enumerate(players):
            player_info = repo.get_player_by_id(player)
            embed.add_field(name=f"Jogador {idx + 1}", value=f"<@{player_info.get('discord_id')}>", inline=True)

        await interaction.message.edit(embed=embed, view=DeleteButtons(players))
        await interaction.response.send_message("Jogador removido!", ephemeral=True)


class DeleteButtons(discord.ui.View):
    def __init__(self, players):
        super().__init__(timeout=None)

        for idx, player in enumerate(players):
            button = DeleteButton(
                label=f"Jogador {idx + 1}",
                custom_id=player,
                style=discord.ButtonStyle.red
            )
            self.add_item(button)


class ResultButtons(discord.ui.View):
    def __init__(self, match_id):
        super().__init__(timeout=None)

        self.match_id = match_id

    @discord.ui.button(label="Vitoria para o time azul", style=discord.ButtonStyle.blurple)
    async def blue_button_callback(self, button, interaction):
        repo.set_match_victory(self.match_id, "BLUE")
        await interaction.message.edit(view=None)

    @discord.ui.button(label="Vitoria para o time vermelho", style=discord.ButtonStyle.red)
    async def red_button_callback(self, button, interaction):
        repo.set_match_victory(self.match_id, "RED")
        await interaction.message.edit(view=None)


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


@bot.slash_command(name="sortear", description="Sortea os times e campeões")
async def sortear(ctx):
    if await block_trolls(ctx):
        await ctx.response.defer()
        players = repo.get_active_players()
        result = generate_team(players)
        match_id = repo.store_match(result)

        blue_embed = generate_embed(result.get("blue_team").get("champions"), discord.Colour.blue())
        red_embed = generate_embed(result.get("red_team").get("champions"), discord.Colour.red())

        blue_team_players = ""
        for idx, player in enumerate(result.get("blue_team").get("players")):
            player_info = repo.get_player_by_id(player)
            player_discord = await bot.fetch_user(player_info.get("discord_id"))
            await player_discord.send(file=blue_embed["file"], embed=blue_embed["embed"])
            blue_team_players += f"{idx + 1} - <@{player_info.get('discord_id')}>\n"

        red_team_players = ""
        for idx, player in enumerate(result.get("red_team").get("players")):
            player_info = repo.get_player_by_id(player)
            player_discord = await bot.fetch_user(player_info.get("discord_id"))
            await player_discord.send(file=red_embed["file"], embed=red_embed["embed"])
            red_team_players += f"{idx + 1} - <@{player_info.get('discord_id')}>\n"

        embed = discord.Embed(
            title="Partidazuda",
            description="Em um embate do bem contra o mal, quem vencera?",
            color=discord.Colour.blurple(),
        )
        embed.add_field(name="Time azul (Lado esquerdo)", value=blue_team_players)
        embed.add_field(name="Time vermelho (Lado direito)", value=red_team_players)
        await ctx.followup.send(embed=embed, view=ResultButtons(match_id))


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
            result += f"{idx+1}º <@{player_map.get(player[0]).get('discord_id')}> - {player[1]} vitorias\n"

        embed = discord.Embed(
            title="Rankzudo",
            description=result
        )

        await ctx.followup.send(embed=embed)


def generate_embed(champions_list, colour):
    champion_string = ""

    rows = math.ceil(len(champions_list) / 5)
    cols = min(len(champions_list), 5)

    fig_width = cols * 2
    fig_height = rows * 2

    fig = plt.figure(figsize=(fig_width, fig_height), facecolor="gray")

    grid = ImageGrid(fig, 111,
                     nrows_ncols=(rows, cols),
                     axes_pad=0.2,
                     )

    for i in range(rows):
        for j in range(cols):
            idx = i * cols + j

            ax = grid[idx]
            if idx < len(champions_list):
                champion_string += f"{champions_list[idx]['name']}\n"
                ax.text(10, 5, champions_list[idx]["name"], bbox={"facecolor": "white", "pad": 1})

                temp_image = imread(champions_list[idx]["image"])
                ax.imshow(temp_image)
                ax.set_xticks([])
                ax.set_yticks([])
            else:
                ax.set_facecolor("none")
                ax.axis("off")

    image_buffer = io.BytesIO()
    fig.savefig(image_buffer, format="png")
    image_buffer.seek(0)

    embed = discord.Embed(
        title="Só os bonecudos",
        description=champion_string,
        color=colour,
    )

    file = discord.File(fp=image_buffer, filename="image.png")
    embed.set_image(url="attachment://image.png")
    return {"embed": embed, "file": file}


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
