import discord
from discord.ext import commands
from reactionmenu import ViewButton, ViewMenu


async def create_dynamic_menu(
    ctx: commands.Context,
    page_counter: str,
    rows: int,
    title: str,
) -> ViewMenu:
    """Create dynamic ReactionMenu.

    This is a type of ReactionMenu, which dynamically creates pages
    based on amount of data. Used for Bootleg and Opener/Closer stats.
    """
    embed = discord.Embed(title=title, description="", color=discord.Color.random())

    menu = ViewMenu(
        ctx,
        menu_type=ViewMenu.TypeEmbedDynamic,
        rows_requested=rows,
        all_can_click=True,
        style=page_counter,
        custom_embed=embed,
        timeout=None,
    )

    back_button = ViewButton(
        style=discord.ButtonStyle.primary,
        label="Back",
        custom_id=ViewButton.ID_PREVIOUS_PAGE,
    )
    menu.add_button(back_button)

    next_button = ViewButton(
        style=discord.ButtonStyle.secondary,
        label="Next",
        custom_id=ViewButton.ID_NEXT_PAGE,
    )
    menu.add_button(next_button)

    return menu


async def create_view_menu(
    ctx: commands.Context,
    style: str = "Page $/&",
    title: str = "",
) -> ViewMenu:
    """Create standard ReactionMenu.

    A type of ReactionMenu, but for arranging a series of embeds
    into pages, reducing clutter when multiple setlists are found.
    """
    embed = discord.Embed(title=title, description="", color=discord.Color.random())

    menu = ViewMenu(ctx, menu_type=ViewMenu.TypeEmbed, style=style, custom_embed=embed)

    # ViewButton.ID_PREVIOUS_PAGE
    back_button = ViewButton(
        style=discord.ButtonStyle.primary,
        label="Back",
        custom_id=ViewButton.ID_PREVIOUS_PAGE,
    )
    menu.add_button(back_button)

    # ViewButton.ID_NEXT_PAGE
    next_button = ViewButton(
        style=discord.ButtonStyle.secondary,
        label="Next",
        custom_id=ViewButton.ID_NEXT_PAGE,
    )
    menu.add_button(next_button)

    return menu
