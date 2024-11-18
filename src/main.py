import discord
import os
import repo
from team_generator.generator import generate_team
from dotenv import load_dotenv

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


def main():
    bot.run(os.getenv('TOKEN'))


if __name__ == "__main__":
    main()
