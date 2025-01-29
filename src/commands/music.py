import logging
import itertools
import functools
import asyncio
import math
import random

import yt_dlp
import repos.firebase_repo as repo
from discord import Bot, ApplicationContext, PCMVolumeTransformer, FFmpegPCMAudio, Embed, Color, Cog, commands, \
    ApplicationCommandError, User, TextChannel
from async_timeout import timeout
from discord.ext.commands import NoPrivateMessage

logging.basicConfig(format='%(levelname)s %(name)s %(asctime)s: %(message)s', level=logging.INFO)
logger = logging.getLogger("c/config")

# Silence useless bug reports messages
yt_dlp.utils.bug_reports_message = lambda: ''

YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}


class VoiceError(Exception):
    pass


class YTDLError(Exception):
    pass


async def search_song(search: str, loop: asyncio.AbstractEventLoop = None):
    loop = loop or asyncio.get_event_loop()

    with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ytdl:
        if search[0:4] != "http" and search[0:3] != "www":
            search = f"ytsearch:{search}"

        partial = functools.partial(ytdl.extract_info, search, download=False, process=False)
        data = await loop.run_in_executor(None, partial)

        if data is None or "entries" not in data:
            raise YTDLError("Não foi possivel achar nenhum resultado.")

        return data["entries"]


def parse_duration(duration: int):
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


async def create_source(url: str, volume: float, *, loop: asyncio.AbstractEventLoop = None):
    loop = loop or asyncio.get_event_loop()

    with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ytdl:

        partial = functools.partial(ytdl.extract_info, url, download=False)
        data = await loop.run_in_executor(None, partial)

        return PCMVolumeTransformer(FFmpegPCMAudio(data['url'], **FFMPEG_OPTIONS), volume=volume)


class Song:
    __slots__ = ('requester', 'channel', 'title', 'thumbnail', 'duration', 'url')

    def __init__(self, song: dict, requester: User, channel: TextChannel):
        self.requester = requester
        self.channel = channel

        self.title = song.get('title')
        self.thumbnail = song.get('thumbnails')[0]['url']
        self.duration = parse_duration(int(song.get('duration')))
        self.url = song.get('url')

    def create_embed(self):
        embed = (Embed(title='Musica adicionada',
                       description='```css\n{0.title}\n```'.format(self),
                       color=Color.random())
                 .add_field(name='Duração', value=self.duration)
                 .add_field(name='Solicitada por', value=self.requester.mention)
                 .add_field(name='URL', value='[Click]({0.url})'.format(self))
                 .set_thumbnail(url=self.thumbnail))

        return embed

    def create_embed_play(self):
        return Embed(description=f"Tocando **{self.title}**")


class SongQueue(asyncio.Queue):
    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))
        else:
            return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return self.qsize()

    def clear(self):
        self._queue.clear()

    def shuffle(self):
        random.shuffle(self._queue)

    def remove(self, index: int):
        del self._queue[index]


class VoiceState:
    def __init__(self, bot: Bot, ctx: ApplicationContext):
        self.bot = bot
        self._ctx = ctx

        self.current = None
        self.voice = None
        self.next = asyncio.Event()
        self.songs = SongQueue()

        self._loop = False
        self._volume = 0.5
        self.skip_votes = set()

        self.audio_player = bot.loop.create_task(self.audio_player_task())

    def __del__(self):
        self.audio_player.cancel()

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, value: bool):
        self._loop = value

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value: float):
        self._volume = value

    @property
    def is_playing(self):
        return self.voice and self.current

    async def audio_player_task(self):
        while True:
            self.next.clear()

            if not self.loop:
                # Try to get the next song within 3 minutes.
                # If no song will be added to the queue in time,
                # the player will disconnect due to performance
                # reasons.
                try:
                    async with timeout(180):  # 3 minutes
                        self.current = await self.songs.get()
                except asyncio.TimeoutError:
                    await self.bot.loop.create_task(self.stop())
                    return

            await self.current.channel.send(embed=self.current.create_embed_play())
            source = await create_source(url=self.current.url, volume=self._volume, loop=self.bot.loop)
            self.voice.play(source, after=self.play_next_song)

            await self.next.wait()

    def play_next_song(self, error=None):
        if error:
            raise VoiceError(str(error))

        self.next.set()

    def skip(self):
        self.skip_votes.clear()

        if self.is_playing:
            self.voice.stop()

    async def stop(self):
        self.songs.clear()

        if self.voice:
            await self.voice.disconnect()
            self.voice = None


class Music(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.voice_states = {}

    def get_voice_state(self, ctx: ApplicationContext):
        state = self.voice_states.get(ctx.guild.id)
        if not state:
            state = VoiceState(self.bot, ctx)
            self.voice_states[ctx.guild.id] = state

        return state

    def cog_unload(self):
        for state in self.voice_states.values():
            self.bot.loop.create_task(state.stop())

    def cog_check(self, ctx: ApplicationContext):
        if not ctx.guild:
            raise NoPrivateMessage('This command can\'t be used in DM channels.')

        return True

    async def cog_before_invoke(self, ctx: ApplicationContext):
        ctx.voice_state = self.get_voice_state(ctx)

    @commands.slash_command(name='join', invoke_without_subcommand=True, description="O bot se junta ao seu canal")
    async def join(self, ctx: ApplicationContext):
        destination = ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            return

        ctx.voice_state.voice = await destination.connect()

    @commands.slash_command(name='leave', aliases=['disconnect'], description="Desconecta o bot e limpa a fila")
    async def leave(self, ctx: ApplicationContext):
        if not ctx.user.guild_permissions.administrator:
            return await ctx.respond('Sem permissão.')

        if not ctx.voice_state.voice:
            return await ctx.respond('O bot não está conectado em nenhum canal.')

        await ctx.voice_state.stop()
        del self.voice_states[ctx.guild.id]
        return await ctx.respond('Desconectado.')

    @commands.slash_command(
        name='now',
        aliases=['current', 'playing'],
        description="Exibe a música tocando tocando no momento"
    )
    async def now(self, ctx: ApplicationContext):
        await ctx.respond(embed=ctx.voice_state.current.create_embed())

    @commands.slash_command(name='pause', description="Pausa a música")
    async def pause(self, ctx: ApplicationContext):
        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_playing():
            ctx.voice_state.voice.pause()
            await ctx.respond('⏹')

    @commands.slash_command(name='resume', description="Continua a música pausada")
    async def resume(self, ctx: ApplicationContext):
        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_paused():
            ctx.voice_state.voice.resume()
            await ctx.respond('⏯')

    @commands.slash_command(name='skip', description="Pula a música")
    async def skip(self, ctx: ApplicationContext):
        if not ctx.voice_state.is_playing:
            return await ctx.respond('Nenhuma música tocando no momento...')

        voter = ctx.interaction.user
        if voter == ctx.voice_state.current.requester:
            await ctx.respond('⏭')
            ctx.voice_state.skip()

        elif voter.id not in ctx.voice_state.skip_votes:
            ctx.voice_state.skip_votes.add(voter.id)
            total_votes = len(ctx.voice_state.skip_votes)

            if total_votes >= 3:
                await ctx.respond('⏭')
                ctx.voice_state.skip()
            else:
                await ctx.respond('Voto para pular a música adicionado, atualmente **{}/3**'.format(total_votes))

        else:
            await ctx.respond('Você já votou para pular essa música.')

    @commands.slash_command(name='queue', description="Exibe as músicas na fila")
    async def queue(self, ctx: ApplicationContext, *, page: int = 1):
        if len(ctx.voice_state.songs) == 0:
            return await ctx.respond('Fila vazia.')

        items_per_page = 10
        pages = math.ceil(len(ctx.voice_state.songs) / items_per_page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue = ''
        for i, song in enumerate(ctx.voice_state.songs[start:end], start=start):
            queue += '`{0}.` [**{1.title}**]({1.url})\n'.format(i + 1, song)

        embed = (Embed(description='**{} tracks:**\n\n{}'.format(len(ctx.voice_state.songs), queue))
                 .set_footer(text='Exibindo página {}/{}'.format(page, pages)))
        await ctx.send(embed=embed)

    @commands.slash_command(name='shuffle', description="Embaralha a fila")
    async def shuffle(self, ctx: ApplicationContext):
        if len(ctx.voice_state.songs) == 0:
            return await ctx.respond('Fila vazia.')

        ctx.voice_state.songs.shuffle()
        await ctx.respond('🔀')

    @commands.slash_command(name='loop', description="Coloca o bot no modo loop")
    async def loop(self, ctx: ApplicationContext):
        if not ctx.voice_state.is_playing:
            return await ctx.send('Nenhuma música tocando no momento.')

        # Inverse boolean value to loop and unloop.
        ctx.voice_state.loop = not ctx.voice_state.loop
        await ctx.respond('🔁')

    @commands.slash_command(name='play', description="Adiciona uma música/playlist a fila")
    async def play(self, ctx: ApplicationContext, *, search: str):
        await ctx.defer()
        if not ctx.voice_state.voice:
            await ctx.invoke(self.join)

        sources = await search_song(search, self.bot.loop)

        for source in sources:
            song = Song(source, ctx.author, ctx.channel)
            await ctx.voice_state.songs.put(song)

        if len(sources) != 1:
            await ctx.followup.send(embed=Embed(description=f"{len(sources)} músicas adicionadas."))
        else:
            await ctx.followup.send(embed=song.create_embed())


    @join.before_invoke
    @play.before_invoke
    async def ensure_voice_state(self, ctx: ApplicationContext):
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise ApplicationCommandError('É necessário estar conectado em um canal para usar esse comando.')

        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                raise ApplicationCommandError('O bot já está conectado a um canal.')


def register_music_commands(bot: Bot):
    bot.add_cog(Music(bot))
