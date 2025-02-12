import asyncio
import os
import logging
import wavelink

from discord import Activity, ActivityType
from discord.bot import Bot
from dotenv import load_dotenv
from commands.match import register_match_commands
from commands.stats import register_stats_commands
from commands.config import register_config_commands
from commands.music import register_music_commands

logging.basicConfig(format='%(levelname)s %(name)s %(asctime)s: %(message)s', level=logging.INFO)
logger = logging.getLogger("main")

load_dotenv()
bot = Bot()
register_stats_commands(bot)
register_match_commands(bot)
register_config_commands(bot)
register_music_commands(bot)


async def connect_nodes():
    await bot.wait_until_ready()

    LAVALINK_URL = os.getenv("LAVALINK_URL")
    LAVALINK_PORT = os.getenv("LAVALINK_PORT")
    LAVALINK_PASSWORD = os.getenv("LAVALINK_PASSWORD")

    nodes = [
        wavelink.Node(
            identifier="Node",
            uri=f"http://{LAVALINK_URL}:{LAVALINK_PORT}",
            password=LAVALINK_PASSWORD
        )
    ]

    await wavelink.Pool.connect(nodes=nodes, client=bot)


@bot.event
async def on_ready():
    logger.info(f"{bot.user} tá on pai!")
    await bot.change_presence(
        activity=Activity(
            type=ActivityType.custom,
            name="custom",
            state="Fraudando as runas...."
        )
    )
    await connect_nodes()


def main():
    TOKEN = os.getenv("TOKEN")
    if not TOKEN:
        raise EnvironmentError("TOKEN is not set in the environment variables.")

    bot.run(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
