import datetime

from cogs.bot_stuff import bot_embed, db, utils, viewmenu
from discord.ext import commands
from psycopg.rows import dict_row

current_date = datetime.datetime.now(tz=datetime.timezone.utc)


class OnThisDay(commands.Cog, name="On This Day"):
    """Collection of commands for searching events by day."""

    def __init__(self, bot: commands.Bot) -> None:
        """Init OnThisDay cog with bot."""
        self.bot = bot
        self.description = "Find events by day"

    @commands.command(name="otd", usage="<date>")
    async def on_this_day(
        self,
        ctx: commands.Context,
        *,
        argument: str = "",
    ) -> None:
        """Find events on a given day, or current day if empty."""
        async with await db.create_pool() as pool:
            await ctx.typing()

            async with pool.connection() as conn, conn.cursor(
                row_factory=dict_row,
            ) as cur:
                if argument == "":
                    date = current_date
                else:
                    date = await utils.date_parsing(argument)

                try:
                    date.strftime("%m-%d")
                except AttributeError:
                    embed = await bot_embed.not_found_embed(
                        command="Events",
                        message=date,
                    )
                    await ctx.send(embed=embed)
                    return

                res = await cur.execute(
                    """
                    SELECT
                        e.formatted_date ||
                        CASE
                            WHEN e1.event_date_note LIKE 'Placeholder%%' THEN ' #' ELSE ''
                        END AS date,
                        e.artist,
                        e.venue_loc AS location,
                        e.event_url AS url
                    FROM "events_with_info" e
                    LEFT JOIN "events" e1 USING(event_id)
                    WHERE e.event_date::text LIKE %(name)s
                    AND e.event_url NOT LIKE '/nogig:'
                    ORDER BY e.event_date;
                    """,  # noqa: E501
                    {"name": f"%{date.strftime("%m-%d")}"},
                )

                otd_results = await res.fetchall()

                if len(otd_results) > 0:
                    menu = await viewmenu.create_dynamic_menu(
                        ctx=ctx,
                        page_counter="Event $ of &",
                        rows=6,
                        title=date.strftime("%B %d"),
                    )

                    data = [
                        f"**{row['artist']}:**\n- [{row['date']} - {row['location']}]({row['url']})\n"  # noqa: E501
                        for row in otd_results
                    ]

                    for row in data:
                        menu.add_row(data=row)

                    await menu.start()
                else:
                    embed = await bot_embed.not_found_embed(
                        command="events",
                        message=date,
                    )
                    await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """Load extension into bot."""
    await bot.add_cog(OnThisDay(bot))
