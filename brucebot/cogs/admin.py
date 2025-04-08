import traceback

import discord
from cogs.bot_stuff import bot_embed
from discord.ext import commands

TESTING = discord.Object(id=735698850802565171)
BRUCE = discord.Object(id=363116664558059521)
SNAKES = discord.Object(id=968567196169146419)


class Admin(commands.Cog):
    """Admin-only commands that make the bot dynamic."""

    def __init__(self, bot: commands.Bot) -> None:
        """Initialize Command."""
        self.bot = bot

    async def cog_command_error(
        self,
        ctx: commands.Context,
        error: Exception,
    ) -> None:
        """Embed to send for any other error that might happen."""
        embed = await bot_embed.error_embed(error)

        print(traceback.format_exc())

        await ctx.send(embed=embed)

    @commands.command(hidden=True, aliases=["re"])
    @commands.is_owner()
    async def reload(self, ctx: commands.Context, extension: str) -> None:
        """Reload the provided extension."""
        try:
            await self.bot.reload_extension(f"cogs.{extension}")
            description = f"{extension} successfully reloaded"
            color = discord.Color.green()
        except commands.ExtensionNotLoaded as e:
            description = f"Failed to reload {extension}\n```{e}```"
            color = discord.Color.red()

        embed = await bot_embed.create_embed(
            ctx=ctx,
            title="Reload",
            description=description,
            color=color,
        )

        await ctx.send(embed=embed)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def load(self, ctx: commands.Context, extension: str) -> None:
        """Load new extension."""
        try:
            await self.bot.load_extension(f"cogs.{extension}")
            description = f"{extension} successfully loaded"
            color = discord.Color.green()
        except commands.ExtensionNotLoaded as e:
            description = f"Failed to load {extension}\n```{e}```"
            color = discord.Color.red()

        embed = await bot_embed.create_embed(
            ctx=ctx,
            title="Reload",
            description=description,
            color=color,
        )

        await ctx.send(embed=embed)

    # I created this when developing locally
    # as it quickly shuts down the bot, as CTRL+C doesn't always work
    # wasn't sure how it would work on heroku, but apparently when the close
    # command is received, heroku attempts to reboot any closed dynos
    # so it acts like a reboot instead
    @commands.command(hidden=True)
    @commands.is_owner()
    async def logout(self, ctx: commands.Context) -> None:
        """Logout and shutdown bot."""
        await ctx.send("Logging Out")
        await self.bot.close()

    @commands.command(hidden=True)
    @commands.is_owner()
    async def clear(self, ctx: commands.Context) -> None:
        """Clear commands."""
        self.bot.tree.clear_commands(guild=None)
        await ctx.bot.tree.sync(guild=None)

        await ctx.send("Cleared Commands")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def sync(self, ctx: commands.Context) -> None:
        """Sync commands."""
        ctx.bot.tree.clear_commands(guild=None)
        guilds = [735698850802565171, 363116664558059521, 968567196169146419]

        await ctx.bot.tree.copy_global_to(guild=TESTING)

        for guild in guilds:
            synced = await ctx.bot.tree.sync(guild=discord.Object(id=guild))

        await ctx.send(f"Cleared tree and synced {len(synced)} commands globally")


async def setup(bot: commands.Bot) -> None:
    """Load extension into bot."""
    await bot.add_cog(Admin(bot))
