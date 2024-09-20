import traceback

import discord
from discord.ext import commands


class Error(commands.Cog):
    """Cog to handle various errors."""

    def __init__(self, bot: commands.Bot) -> None:
        """Initialize Command."""
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(
        self,
        ctx: commands.Context,
        error: commands.CommandError,
    ) -> None:
        """Embed to send for any other error that might happen."""
        embed = discord.Embed(
            title="Error",
            description=f"```{error}```",
            color=discord.Color.red(),
        )

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send_help(ctx.command)
        else:
            print(
                "".join(
                    traceback.format_exception(type(error), error, error.__traceback__),
                ),
            )

            await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """Load extension into bot."""
    await bot.add_cog(Error(bot))
