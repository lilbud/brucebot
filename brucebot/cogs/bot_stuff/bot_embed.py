import discord
from discord.ext import commands

DEFAULT_COLOR = discord.Color.random()


async def create_embed(
    ctx: commands.Context,
    title: str = "",
    description: str = "",
    url: str = "",
    color: discord.colour = DEFAULT_COLOR,
) -> discord.Embed:
    """Create a discord embed.

    Sets the embed author/icon, as well as the color if provided.
    Or a random color if none provided.
    """
    return discord.Embed(
        title=title,
        description=description,
        url=url,
        color=color,
    ).set_author(
        name=f"Requested by: {ctx.author.display_name}",
        icon_url=str(ctx.author.avatar.url),
    )


async def error_embed(error: Exception) -> discord.Embed:
    """Embed to send upon any errors.

    This embed will be called and sent if any cog_command_error occurs.
    """
    return discord.Embed(
        title="Error",
        description=f"```{error}```",
        color=discord.Color.red(),
    )


async def not_found_embed(
    command: str,
    message: str,
) -> discord.Embed:
    """Embed if no results found for the given query."""
    return discord.Embed(
        title="""You ain't gonna find nothin' down here friend,\nExcept seeds blowin' up the highway in the south wind""",  # noqa: E501
        description=f"No {command} found for `{message}`",
        color=discord.Color.red(),
    )
