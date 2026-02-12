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

    @commands.hybrid_command(
        name="onthisday",
        aliases=["otd"],
        description="Find events on a given day, or current day if empty.",
        usage="<date>",
    )
    async def on_this_day(
        self,
        ctx: commands.Context,
        *,
        date: str = "",
    ) -> None:
        """Find events on a given day, or current day if empty."""
        async with (
            await db.create_pool() as pool,
            pool.connection() as conn,
            conn.cursor(
                row_factory=dict_row,
            ) as cur,
        ):
            if date == "":
                date = current_date
            else:
                date = await utils.date_parsing(date)

            try:
                date.strftime("%m-%d")
            except AttributeError:
                embed = await bot_embed.not_found_embed(
                    command="Events on this day",
                    message=date,
                )
                await ctx.send(embed=embed)
                return

            res = await cur.execute(
                """
                    SELECT
                    e.event_type,
                    to_char(e.event_date, 'YYYY-MM-DD [Dy]')||
                    CASE WHEN e.event_date is null then ' #' else '' end as date,
                    b.name AS artist,
                    e.event_id,
                    CASE WHEN c1.id in (2,6,37)
                        then concat_ws(', ', v.name, c.name, s.state_abbrev)
                        else concat_ws(', ', v.name, c.name, s.name, c1.name)
                    end as formatted_loc
                    FROM "events" e
                    LEFT JOIN bands b ON b.id = e.artist
                    left join venues v on v.id = e.venue_id
                    left join cities c on c.id = v.city
                    left join states s on s.id = c.state
                    left join countries c1 on c1.id = c.country
                    WHERE e.event_date::text LIKE %(date)s
                    ORDER BY e.event_id
                    """,
                {"date": f"%{date.strftime('%m-%d')}"},
            )

            otd_results = await res.fetchall()

            if len(otd_results) > 0:
                menu = await viewmenu.create_dynamic_menu(
                    ctx=ctx,
                    page_counter="Event $/&\nEvents with # are placeholder dates",
                    rows=6,
                    title=date.strftime("%B %d"),
                )

                data = [
                    f"**{row['artist']}:**\n- [{row['date']} - {row['formatted_loc']}](https://www.databruce.com/events/{row['event_id']}) [{row['event_type']}]\n"  # noqa: E501
                    for row in otd_results
                ]

                for row in data:
                    menu.add_row(data=row)

                await menu.start()
            else:
                embed = await bot_embed.not_found_embed(
                    command="Events on this day",
                    message=date,
                )
                await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """Load extension into bot."""
    await bot.add_cog(OnThisDay(bot))
