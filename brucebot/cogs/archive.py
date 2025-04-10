from cogs.bot_stuff import bot_embed, db, utils, viewmenu
from discord.ext import commands
from psycopg.rows import dict_row


class Archive(commands.Cog):
    """Collection of commands to find shows on archive.org."""

    def __init__(self, bot: commands.bot) -> None:
        """Init Bootleg cog with bot."""
        self.bot = bot
        self.description = "Find bootlegs by date"

    async def archive_latest(self, shows: dict, ctx: commands.Context) -> None:
        """Archive default command, show 10 latest shows."""
        menu = await viewmenu.create_dynamic_menu(
            ctx=ctx,
            page_counter="Page $/&",
            rows=10,
            title="Latest shows added to Radio Nowhere @ archive.org",
        )

        for index, show in enumerate(shows, start=1):
            added_date = show["created_at"]

            row = f"{index}. [{show['archive_url'][28:]}]({show['archive_url']})\n\tAdded: {added_date.strftime('%Y-%m-%d - %I:%M %p')}"  # noqa: E501

            menu.add_row(row)

        await menu.start()

    async def archive_embed(
        self,
        date: str,
        shows: dict,
        ctx: commands.Context,
    ) -> None:
        """Embed for getting results from Archive.org."""
        menu = await viewmenu.create_dynamic_menu(
            ctx=ctx,
            page_counter="Page $/&",
            rows=6,
            title=f"Radio Nowhere @ archive.org results for:\n{date}",
        )

        for index, show in enumerate(shows, start=1):
            added_date = show["created_at"]

            row = f"{index}. [{show['archive_url'][28:]}]({show['archive_url']})\n\tAdded: {added_date.strftime('%Y-%m-%d %I:%M %p')}"  # noqa: E501

            menu.add_row(row)

        await menu.start()

    @commands.hybrid_command(
        name="archive",
        aliases=["ar"],
        description="Search the Radio Nowhere archive by date",
        usage="<date>",
    )
    async def get_archive_shows(  # noqa: D102
        self,
        ctx: commands.Context,
        *,
        date: str = "",
    ) -> None:
        async with (
            await db.create_pool() as pool,
            pool.connection() as conn,
            conn.cursor(
                row_factory=dict_row,
            ) as cur,
        ):
            if date:
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

                result = await cur.execute(
                    """
                        SELECT
                            e.event_date,
                            a.archive_url,
                            a.created_at
                        FROM archive_links a
                        LEFT JOIN events e USING(event_id)
                        WHERE e.event_date::text = %(query)s
                        """,
                    {"query": date.strftime("%Y-%m-%d")},
                )

                shows = await result.fetchall()

                if shows:
                    await self.archive_embed(date, shows, ctx)
                else:
                    embed = await bot_embed.not_found_embed(
                        command=self.__class__.__name__,
                        message=date,
                    )
                    await ctx.send(embed=embed)

            else:
                result = await cur.execute(
                    """
                        SELECT
                            e.event_date,
                            a.archive_url,
                            a.created_at
                        FROM archive_links a
                        LEFT JOIN events e USING(event_id)
                        ORDER BY a.created_at DESC LIMIT 10
                        """,
                )

                shows = await result.fetchall()

                if shows:
                    await self.archive_latest(shows, ctx)


async def setup(bot: commands.Bot) -> None:
    """Load extension into bot."""
    await bot.add_cog(Archive(bot))
