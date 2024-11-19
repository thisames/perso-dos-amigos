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
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="Enviando mentiras..."))


class SelectTimeView(discord.ui.View):
    @discord.ui.select(
        placeholder="Escolha os jogadores ativos!",
        min_values=1,
        max_values=repo.get_players_max_size(),
        options=repo.get_players()
    )
    async def select_callback(self, select, interaction):
        print(select.values)
        repo.add_active_players(select.values)
        await interaction.message.edit(f"Segue a lista de viados: {select.values}", view=None)


@bot.slash_command(name="montar")
async def montar(ctx):
    try:
        await ctx.response.defer()
        await ctx.followup.send("Monta o time!", view=SelectTimeView())
    except Exception as e:
        print(repr(e))


@bot.slash_command(name="limpar")
async def limpar(ctx):
    try:
        await ctx.response.defer()
        repo.clear_active_players()
        await ctx.followup.send("A lista de jogadores ativos foi esvaziada!")
    except Exception as e:
        print(repr(e))


@bot.slash_command(name="time", description="Mostra o timezudo on")
async def time(ctx):
    try:
        await ctx.response.defer()
        await ctx.followup.send("Timezudo on doidão")
    except Exception as e:
        print(repr(e))


@bot.slash_command(name="sortear", description="Sortea os times e campeões")
async def sortear(ctx, qnt_champions):
    await ctx.response.defer()
    players = repo.get_active_players()
    result = generate_team(players)
    print(result)
    await ctx.followup.send("Timezudo on doidão")


@bot.slash_command(name="registrar", description="Adicionar jogador")
async def registrar(ctx, nome: str, user: discord.User):
    try:
        await ctx.response.defer()
        repo.set_player(nome, user)
        await ctx.followup.send(f"{nome} registrado com sucesso.")
    except Exception as e:
        print(repr(e))


@bot.slash_command(name = "envio_imagem", description = "eita")
async def foo(ctx):
    images = ["https://ddragon.leagueoflegends.com/cdn/14.22.1/img/champion/Aatrox.png" for _ in range(6)]

    rows = math.ceil(len(images) / 5)
    cols = min(len(images), 5)

    fig_width = cols * 2
    fig_height = rows * 2

    fig = plt.figure(figsize=(fig_width, fig_height),facecolor='gray')

    grid = ImageGrid(fig, 111,  # similar to subplot(111)
                     nrows_ncols=(rows, cols),  # creates 2x2 grid of axes
                     axes_pad=0.2,  # pad between axes in inch.
     )

    for i in range(rows):
        for j in range(cols):
            idx = i * cols + j


            ax = grid[idx]
            if idx < len(images):
                ax.text(10, 5, "Aatrox", bbox={'facecolor': 'white', 'pad': 1})

                temp_image = imread(images[idx])
                ax.imshow(temp_image)
                ax.set_xticks([])
                ax.set_yticks([])
            else:
                ax.set_facecolor('none')
                ax.axis('off')

    image_buffer = io.BytesIO()
    fig.savefig(image_buffer, format='png')
    image_buffer.seek(0)


    embed = discord.Embed(
        title = "Campeões",
        color=discord.Color.green()
    )

    file = discord.File(fp=image_buffer, filename='image.png')
    embed.set_image(url='attachment://image.png')

    await ctx.respond(file = file, embed=embed)

def main():
    bot.run(os.getenv('TOKEN'))


if __name__ == "__main__":
    main()
