import logging
import math
import re
import typing
import wavelink

from discord import Embed, Color, commands, ClientException, Option, OptionChoice
from discord.bot import Bot
from discord.cog import Cog
from discord.commands import ApplicationContext

logging.basicConfig(format='%(levelname)s %(name)s %(asctime)s: %(message)s', level=logging.INFO)
logger = logging.getLogger("c/config")

url_rx = re.compile(r'https?://(?:www\.)?.+')


def parse_duration(duration: int):
    duration = duration//1000

    minutes, seconds = divmod(duration, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    duration = []
    if days > 0:
        duration.append('{} dias'.format(days))
    if hours > 0:
        duration.append('{} horas'.format(hours))
    if minutes > 0:
        duration.append('{} minutos'.format(minutes))
    if seconds > 0:
        duration.append('{} segundos'.format(seconds))

    return ', '.join(duration)


class Music(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        payload.node.inactive_channel_tokens = 1
        payload.node.inactive_timeout = 60

    @Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        player: wavelink.Player | None = payload.player
        if not player:
            # Handle edge cases...
            return

        track: wavelink.Playable = payload.track

        embed: Embed = Embed(title="Tocando agora", color=Color.random())
        embed.description = f"```\n{track.title}\n```"

        embed.add_field(name='Autor', value=track.author)
        embed.add_field(name='Duração', value=parse_duration(track.length))
        embed.add_field(name='URL', value=f'[Click]({track.uri})')

        if track.artwork:
            embed.set_thumbnail(url=track.artwork)

        await player.home.send(embed=embed)

    @Cog.listener()
    async def on_wavelink_inactive_player(self, player: wavelink.Player):
        await player.home.send(embed=Embed(description="O bot está inativo. Desconectando", color=Color.red()))
        await player.disconnect()

    @commands.slash_command(name="play")
    async def play(
            self,
            ctx: ApplicationContext,
            search: str,
            priority: Option(int, "A musica será colocada no inicio da fila", default=False,
                             choices=[OptionChoice("Sim", value=True), OptionChoice("Não", value=False)])):

        await ctx.defer()
        if not ctx.guild:
            return

        player: wavelink.Player
        player = typing.cast(wavelink.Player, ctx.voice_client)  # type: ignore

        if not player:
            try:
                player = await ctx.author.voice.channel.connect(cls=wavelink.Player)  # type: ignore
            except AttributeError:
                await ctx.followup.send("Para utilizar esse comando, se conecte a um canal.")
                return
            except ClientException:
                await ctx.followup.send("Não foi possivel se conectar ao canal. Tente novamente.")
                return

        # Turn on AutoPlay to enabled mode.
        # enabled = AutoPlay will play songs for us and fetch recommendations...
        # partial = AutoPlay will play songs for us, but WILL NOT fetch recommendations...
        # disabled = AutoPlay will do nothing...
        player.autoplay = wavelink.AutoPlayMode.partial

        # Lock the player to this channel...
        if not hasattr(player, "home"):
            player.home = ctx.channel
        elif player.home != ctx.channel:
            await ctx.followup.send(
                f"O bot já está conectado ao canal {player.home.mention}.")
            return

        # This will handle fetching Tracks and Playlists...
        # Seed the doc strings for more information on this method...
        # If spotify is enabled via LavaSrc, this will automatically fetch Spotify tracks if you pass a URL...
        # Defaults to YouTube for non URL based queries...
        tracks: wavelink.Search = await wavelink.Playable.search(search)
        if not tracks:
            await ctx.followup.send("Não foi possivel localizar nenhum resultado para essa busca.")
            return

        embed = Embed(color=Color.blurple())

        if isinstance(tracks, wavelink.Playlist):
            if priority:
                added: int = 0
                for track in reversed(tracks):
                    added += 1
                    player.queue.put_at(0, track)
            else:
                added: int = await player.queue.put_wait(tracks)

            embed.title = 'Playlist enfileirada!'
            embed.description = f'**{tracks.name}** - {added} tracks'

            if tracks.artwork:
                embed.set_thumbnail(url=tracks.artwork)
        else:
            track: wavelink.Playable = tracks[0]
            if priority:
                player.queue.put_at(0, track)
            else:
                await player.queue.put_wait(track)

            embed.title = 'Música enfileirada!'
            embed.description = f'[{track}]({track.uri})'

        await ctx.followup.send(embed=embed)

        if not player.playing:
            await player.play(player.queue.get(), volume=30)

    @commands.slash_command(name='skip', description="Pula a música")
    async def skip(self, ctx: ApplicationContext):
        player: wavelink.Player = typing.cast(wavelink.Player, ctx.voice_client)
        if not player:
            ctx.respond("O bot não está conectado.")
            return

        await player.skip(force=True)
        await ctx.respond("⏭")

    @commands.slash_command(name="toggle", aliases=["pause", "resume"])
    async def pause_resume(self, ctx: ApplicationContext):
        player: wavelink.Player = typing.cast(wavelink.Player, ctx.voice_client)
        if not player:
            ctx.respond("O bot não está conectado.")
            return

        await player.pause(not player.paused)
        await ctx.respond("⏯️")

    @commands.slash_command(name="leave")
    async def leave(self, ctx: ApplicationContext):
        player: wavelink.Player = typing.cast(wavelink.Player, ctx.voice_client)
        if not player:
            ctx.respond("O bot não está conectado.")
            return

        await player.disconnect()
        await ctx.respond("Bot desconectado.")

    @commands.slash_command(name="shuffle")
    async def shuffle(self, ctx: ApplicationContext):
        player: wavelink.Player = typing.cast(wavelink.Player, ctx.voice_client)
        if not player:
            ctx.respond("O bot não está conectado.")
            return

        player.queue.shuffle()
        await ctx.respond("🔀")

    @commands.slash_command(name='queue')
    async def queue(self, ctx: ApplicationContext, *, page: int = 1):
        player: wavelink.Player = typing.cast(wavelink.Player, ctx.voice_client)
        if not player:
            ctx.respond("O bot não está conectado.")
            return

        items_per_page = 10
        pages = math.ceil(len(player.queue) / items_per_page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue = ''
        for i, song in enumerate(player.queue[start:end], start=start):
            queue += '`{0}.` [**{1.title}**]({1.uri})\n'.format(i + 1, song)

        embed = (Embed(description='**{} Músicas:**\n\n{}'.format(len(player.queue), queue))
                 .set_footer(text='Exibindo página {}/{}'.format(page, pages)))
        await ctx.respond(embed=embed)


def register_music_commands(bot: Bot):
    bot.add_cog(Music(bot))
