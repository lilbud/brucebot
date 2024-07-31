from discord.ext import commands


class Info(commands.Cog):
    """Collection of commands for pulling setlists for different shows."""

    def __init__(self, bot: commands.Bot) -> None:
        """Init Setlist cog with bot."""
        self.bot = bot
        self.description = "Bot/Database Info"


async def setup(bot: commands.Bot) -> None:
    """Load extension into bot."""
    await bot.add_cog(Info(bot))
