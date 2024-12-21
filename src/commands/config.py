import logging
import repos.firebase_repo as repo

from discord import Bot, ApplicationContext

logging.basicConfig(format='%(levelname)s %(name)s %(asctime)s: %(message)s', level=logging.INFO)
logger = logging.getLogger("c/config")


def register_config_commands(bot: Bot):
    @bot.slash_command(name="season", description="Cria uma season nova")
    async def create_season(
            ctx: ApplicationContext
    ):
        await ctx.response.defer()
        if not ctx.user.guild_permissions.administrator:
            await ctx.followup.send("Somente admins podem usar esse comando")
            return

        new_season = await repo.create_new_season()

        await ctx.followup.send(f"# Season {new_season.get('id')} iniciada!")
