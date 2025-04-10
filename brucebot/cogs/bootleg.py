import datetime

import psycopg
from cogs.bot_stuff import bot_embed, db, utils, viewmenu
from discord.ext import commands
from psycopg.rows import dict_row
from reactionmenu import ViewButton


class Bootleg(commands.Cog):
    """Collection of commands to find bootlegs."""

    def __init__(self, bot: commands.bot) -> None:
        """Init Bootleg cog with bot."""
        self.bot = bot
        self.description = "Find bootlegs by date"

    async def media_to_emote(self, media_type: str) -> str:
        """Match emotes to media types."""
        match media_type:
            case "DVD":
                return "📀"
            case "Blu-Ray" | "CD":
                return "💿"
            case "FLAC":
                return "📁"
            case "Vinyl":
                return "🎵"
            case _:
                return ""

    async def bootleg_embed(
        self,
        ctx: commands.Context,
        bootlegs: list,
        date: str,
    ) -> None:
        """Embed for bootlegs, splits entries over pages."""
        menu = await viewmenu.create_dynamic_menu(
            ctx=ctx,
            page_counter="Page $/&\nData gathered from SpringsteenLyrics",
            rows=6,
            title=f"Bootleg results for:\n{date} - {bootlegs[0]['venue_loc']}",
        )

        sp_lyrics_button = ViewButton(
            style="link",
            label="SpringsteenLyrics",
            url=f"https://www.springsteenlyrics.com/bootlegs.php?filter_date={date}&cmd=list&category=filter_date",
        )

        menu.add_button(sp_lyrics_button)

        for boot in bootlegs:
            emote = await self.media_to_emote(media_type=boot["media_type"])
            row = f"**{boot['label']}** - {boot['title']}\n{emote}  {boot['media_type']} - *{boot['category']}*\n"  # noqa: E501

            if boot["slid"] is not None:
                url = await utils.format_link(
                    url=f"https://www.springsteenlyrics.com/bootlegs.php?item={boot['slid']}",
                    text=boot["title"],
                )

                row = f"**{boot['label']}** - {url}\n{emote}  {boot['media_type']} - *{boot['category']}*\n"  # noqa: E501

            menu.add_row(data=row)

        await menu.start()

    async def bootleg_search(
        self,
        date: datetime.datetime,
        cur: psycopg.AsyncCursor,
    ) -> dict:
        """Search for bootlegs."""
        res = await cur.execute(
            """
            SELECT
                DISTINCT unaccent(b.title) AS title,
                b.label,
                b.slid,
                CASE
                    WHEN b.category = 'aud_comp' THEN 'Audio Compilation'
                    WHEN b.category = 'vid_comp' THEN 'Video Compilation'
                    WHEN b.category SIMILAR TO 'aud_*' THEN 'Audio'
                    WHEN b.category SIMILAR TO 'vid_*' THEN 'Video'
                END as category,
                b.media_type,
                v.formatted_loc AS venue_loc
            FROM "bootlegs" b
            LEFT JOIN "events_with_info" e ON e.event_id = b.event_id
            LEFT JOIN "venues_text" v ON v.id = e.venue_id
            WHERE e.event_date = %(query)s
            ORDER BY title ASC
            """,
            {"query": date.strftime("%Y-%m-%d")},
        )

        return await res.fetchall()

    @commands.hybrid_command(
        name="bootleg",
        aliases=["boot"],
        description="Get a list bootlegs by date",
        usage="<date>",
    )
    async def get_bootlegs(
        self,
        ctx: commands.Context,
        *,
        date: str,
    ) -> None:
        """Search database for bootlegs by date.

        Date can be in any valid format, although YYYY-MM-DD is recommended.
        """
        async with await db.create_pool() as pool:
            date = await utils.date_parsing(date)

            try:
                date.strftime("%Y-%m-%d")
            except AttributeError:
                embed = await bot_embed.not_found_embed(
                    command=self.__class__.__name__,
                    message=date,
                )
                await ctx.send(embed=embed)
                return

            async with (
                pool.connection() as conn,
                conn.cursor(
                    row_factory=dict_row,
                ) as cur,
            ):
                bootlegs = await self.bootleg_search(date=date, cur=cur)

                print(bootlegs[0])

            if len(bootlegs) > 0:
                await self.bootleg_embed(
                    ctx=ctx,
                    bootlegs=bootlegs,
                    date=date.strftime("%Y-%m-%d"),
                )
            else:
                embed = await bot_embed.not_found_embed(
                    command=self.__class__.__name__,
                    message=date,
                )
                await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """Load extension into bot."""
    await bot.add_cog(Bootleg(bot))
