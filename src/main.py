import discord
import os
import logging

from dotenv import load_dotenv
from commands.match import register_match_commands
from commands.stats import register_stats_commands
from commands.config import register_config_commands
from commands.music import register_music_commands

logging.basicConfig(format='%(levelname)s %(name)s %(asctime)s: %(message)s', level=logging.INFO)
logger = logging.getLogger("main")

load_dotenv()
bot = discord.Bot()
register_stats_commands(bot)
register_match_commands(bot)
register_config_commands(bot)
register_music_commands(bot)


@bot.event
async def on_ready():
    logger.info(f"{bot.user} tá on pai!")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.custom,
            name="custom",
            state="Fraudando as runas...."
        )
    )


def main():
    TOKEN = os.getenv("TOKEN")
    if not TOKEN:
        raise EnvironmentError("TOKEN is not set in the environment variables.")

    bot.run(TOKEN)


if __name__ == "__main__":
    main()
