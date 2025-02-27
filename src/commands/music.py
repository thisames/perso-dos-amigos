import colorsys
import logging
import math
import random
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
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        player: wavelink.Player | None = payload.player
        if not player:
            # Handle edge cases...
            return

        track: wavelink.Playable = payload.original

        colour = colorsys.hls_to_rgb(
            random.randint(20, 241)/360,
            0.7 + 0.2 * (random.randint(0, 100) / 100),
            0.3 + 0.4 * (random.randint(0, 100)/100)
        )

        embed: Embed = Embed(
            title=f"{track.title}{' - ' + track.author if track.author else ''}",
            color=Color.from_rgb(int(colour[0] * 255), int(colour[1] * 255), int(colour[2] * 255)),
            url=track.uri
        )

        embed.add_field(name='Solicitado por', value=track.requester.mention)
        embed.add_field(name='Duração', value=parse_duration(track.length))

        if track.artwork:
            embed.set_thumbnail(url=track.artwork)

        await player.home.send(embed=embed)

    @Cog.listener()
    async def on_wavelink_inactive_player(self, player: wavelink.Player):
        await player.home.send(embed=Embed(description="O bot está inativo. Desconectando... <a:exit:1343976292424618146> ", color=Color.red()))
        player.cleanup()
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
                await ctx.followup.send("Para utilizar esse comando, se conecte a um canal. <a:no:1343975451483181076>")
                return
            except ClientException:
                await ctx.followup.send("Não foi possivel se conectar ao canal. Tente novamente. <a:hmm:1343977260767772744>")
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
                f"O bot já está conectado ao canal {player.home.mention}. <a:no:1343975451483181076> ")
            return

        # This will handle fetching Tracks and Playlists...
        # Seed the doc strings for more information on this method...
        # If spotify is enabled via LavaSrc, this will automatically fetch Spotify tracks if you pass a URL...
        # Defaults to YouTube for non URL based queries...
        tracks: wavelink.Search = await wavelink.Playable.search(search)
        if not tracks:
            await ctx.followup.send("Não foi possivel localizar nenhum resultado para essa busca. <a:hmm:1343977260767772744>")
            return

        embed = Embed(color=Color.blurple())

        for track in tracks:
            track.requester = ctx.author

        if isinstance(tracks, wavelink.Playlist):
            if priority:
                added: int = 0
                for track in reversed(tracks):
                    added += 1
                    player.queue.put_at(0, track)
            else:
                added: int = await player.queue.put_wait(tracks)

            embed.title = 'Playlist enfileirada! <a:dj:1343976753080569906>'
            embed.description = f'**{tracks.name}** - {added} tracks'

            if tracks.artwork:
                embed.set_thumbnail(url=tracks.artwork)
        else:
            track: wavelink.Playable = tracks[0]
            if priority:
                player.queue.put_at(0, track)
            else:
                await player.queue.put_wait(track)

            embed.title = 'Música enfileirada! <a:dj:1343976753080569906>'
            embed.description = f'[{track}]({track.uri})'

        await ctx.followup.send(embed=embed)

        if not player.playing:
            await player.play(player.queue.get(), volume=30)

    @commands.slash_command(name="remove", description="Remove a ultima música da fila")
    async def remove(self, ctx: ApplicationContext):
        player: wavelink.Player = typing.cast(wavelink.Player, ctx.voice_client)
        if not player:
            await ctx.respond(embed=Embed(description="O bot não está conectado. <a:no:1343975451483181076>"))
            return

        try:
            player.queue.delete(player.queue.count - 1)
            await ctx.respond(embed=Embed(description="Música removida da fila. <a:erase:1344810860333502484>"))
        except IndexError:
            await ctx.respond(embed=Embed(description="Falha ao remover música da fila. <a:injuried:1344811318120550400>"))

    @commands.slash_command(name="clear", description="Remove todas as músicas da fila")
    async def clear(
            self,
            ctx: ApplicationContext):
        player: wavelink.Player = typing.cast(wavelink.Player, ctx.voice_client)
        if not player:
            await ctx.respond(embed=Embed(description="O bot não está conectado. <a:no:1343975451483181076>"))
            return

        player.queue.reset()
        await ctx.respond(embed=Embed(description="Fila limpa. <a:clean:1344809977315070088>"))

    @commands.slash_command(name="volume", description="Ajusta o volume do bot")
    async def volume(
            self,
            ctx: ApplicationContext,
            volume: Option(int, min_value=0, max_value=200)
    ):
        player: wavelink.Player = typing.cast(wavelink.Player, ctx.voice_client)
        if not player:
            await ctx.respond(embed=Embed(description="O bot não está conectado. <a:no:1343975451483181076>"))
            return

        await player.set_volume(volume)
        await ctx.respond(f"Volume definido para {volume}%. <a:fix:1344807701158432858>")

    @commands.slash_command(name='skip', description="Pula a música")
    async def skip(self, ctx: ApplicationContext):
        player: wavelink.Player = typing.cast(wavelink.Player, ctx.voice_client)
        if not player:
            await ctx.respond(embed=Embed(description="O bot não está conectado. <a:no:1343975451483181076>"))
            return

        await player.skip(force=True)
        await ctx.respond("<a:fazol:1343975050138746890>")

    @commands.slash_command(name="pause", aliases=["pause", "resume"])
    async def pause(self, ctx: ApplicationContext):
        player: wavelink.Player = typing.cast(wavelink.Player, ctx.voice_client)
        if not player:
            await ctx.respond(embed=Embed(description="O bot não está conectado. <a:no:1343975451483181076>"))
            return

        await player.pause(not player.paused)
        await ctx.respond("<a:pause:1343974955536224266>" if player.paused else "<a:play:1343974896669032511>")

    @commands.slash_command(name="leave")
    async def leave(self, ctx: ApplicationContext):
        player: wavelink.Player = typing.cast(wavelink.Player, ctx.voice_client)
        if not player:
            await ctx.respond(embed=Embed(description="O bot não está conectado. <a:no:1343975451483181076>"))
            return

        player.cleanup()
        await player.disconnect()
        await ctx.respond(embed=Embed(description="Bot desconectado. <a:exit:1343976292424618146>"))

    @commands.slash_command(name="shuffle")
    async def shuffle(self, ctx: ApplicationContext):
        player: wavelink.Player = typing.cast(wavelink.Player, ctx.voice_client)
        if not player:
            await ctx.respond(embed=Embed(description="O bot não está conectado. <a:no:1343975451483181076>"))
            return

        player.queue.shuffle()
        await ctx.respond("<a:shuffle:1343972431324385363>")

    @commands.slash_command(name='queue')
    async def queue(self, ctx: ApplicationContext, *, page: int = 1):
        player: wavelink.Player = typing.cast(wavelink.Player, ctx.voice_client)
        if not player:
            await ctx.respond(embed=Embed(description="O bot não está conectado. <a:no:1343975451483181076>"))
            return

        if len(player.queue) == 0:
            await ctx.respond(embed=Embed(description="Fila vazia <a:dormir:1344806036200230963>"))
            return

        items_per_page = 10
        pages = max(math.ceil(len(player.queue) / items_per_page), 1)

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
