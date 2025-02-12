import discord
import logging
import repos.firebase_repo as repo

from discord.bot import Bot
from discord.commands import Option, OptionChoice
from discord_model.view import TeamSelectView, DeleteButtons, ResultButtons
from repos.champions_repo import ImageDict
from team_generator.generator import generate_team
from utils.embed import create_champion_embed, create_active_players_embed, create_active_team_embed

logging.basicConfig(format='%(levelname)s %(name)s %(asctime)s: %(message)s', level=logging.INFO)
logger = logging.getLogger("c/match")


def register_match_commands(bot: Bot):
    data = ImageDict()

    @bot.slash_command(name="adicionar", description="Adiciona jogadores a lista de ativos")
    async def add_active_players(
            ctx: discord.ApplicationContext,
            fixed: Option(int, "Os times serão fixos", name="fixos", default=False,
                          choices=[OptionChoice("Sim", value=True), OptionChoice("Não", value=False)])):
        await ctx.response.defer(ephemeral=True)
        if fixed:
            await repo.set_config("fixed_teams", True)
            await ctx.followup.send("Monte os times!", view=TeamSelectView(["A", "B"]))
        else:
            if await repo.get_config("fixed_teams"):
                await ctx.followup.send("Modo de times fixos, caso queira alterar use o /limpar!")
                return

            await ctx.followup.send("Monta o time!", view=TeamSelectView())

    @bot.slash_command(
        name="canal",
        description="Adiciona os jogadores que estão em um determinado canal a lista de ativos"
    )
    async def add_channel_active_players(
            ctx: discord.ApplicationContext
    ):
        await ctx.response.defer(ephemeral=True)
        member = ctx.guild.get_member(ctx.user.id)
        voice = member.voice

        if not voice:
            await ctx.followup.send("É necessário estar conectado a um canal de voz para executar esse comando!")
            return

        await repo.add_active_players(list(voice.channel.voice_states))

        await ctx.followup.send(f"Os jogadores do canal {voice.channel.name} foram adicionados a lista de ativos!")

    @bot.slash_command(name="limpar", description="Apaga todos os jogadores da lista de ativos")
    async def clear_active_players(ctx):
        await ctx.response.defer(ephemeral=True)
        await repo.clear_active_players()
        await ctx.followup.send("A lista de jogadores ativos foi esvaziada!")

    @bot.slash_command(name="ativos", description="Mostra os jogadores ativos")
    async def list_active_players(ctx):
        await ctx.response.defer()
        players = await repo.get_active_players()

        if await repo.get_config("fixed_teams"):
            embed = create_active_team_embed(players)
            await ctx.followup.send(embed=embed)
        else:
            embed = create_active_players_embed(players)
            await ctx.followup.send(embed=embed, view=DeleteButtons(players))

    async def send_embed(player_info, embed):
        player_discord = await bot.fetch_user(player_info.get("discord_id"))

        try:
            embed["file"].seek(0)
            file = discord.File(fp=embed["file"], filename="image.png")

            await player_discord.send(file=file, embed=embed["embed"])
        except Exception as e:
            logger.warning(f"Failed to send message to user {player_discord.name}, cause: {e}")

    @bot.slash_command(name="sortear", description="Sortea os times e campeões")
    async def sort_active_players(ctx, choices_number: Option(int, "Quantidade de campeões", name="opções", default=0,
                                                              min_value=1, max_value=10)):
        await ctx.response.defer()
        players = await repo.get_active_players()
        result = generate_team(players, list(data), await repo.get_config("fixed_teams"), choices_number)
        match_id = await repo.store_match(result)

        blue_embed = create_champion_embed(result.get("blue_team").get("champions"), data, discord.Colour.blue(), 1)
        red_embed = create_champion_embed(result.get("red_team").get("champions"), data, discord.Colour.red(), 2)

        blue_team_players = ""
        for idx, player in enumerate(result.get("blue_team").get("players")):
            blue_team_players += f"{idx + 1} - <@{player.get('discord_id')}>\n"
            await send_embed(player, blue_embed)

        red_team_players = ""
        for idx, player in enumerate(result.get("red_team").get("players")):
            red_team_players += f"{idx + 1} - <@{player.get('discord_id')}>\n"
            await send_embed(player, red_embed)

        embed = discord.Embed(
            title="Partidazuda",
            description="Em um embate do bem contra o mal, quem vencerá?",
            color=discord.Colour.blurple(),
        )
        embed.add_field(name="Time azul (Lado esquerdo)", value=blue_team_players)
        embed.add_field(name="Time vermelho (Lado direito)", value=red_team_players)
        await ctx.followup.send(embed=embed, view=ResultButtons(match_id, ctx.author.id))

    @bot.slash_command(name="registrar", description="Adicionar jogador")
    async def register_new_player(ctx, nome: str, user: discord.User):
        await ctx.response.defer(ephemeral=True)
        await repo.set_player(nome, user)
        await ctx.followup.send(f"{nome} registrado com sucesso.")
