from pathlib import Path

import discord
import psycopg
from cogs.bot_stuff import bot_embed, db
from discord.ext import commands
from psycopg.rows import dict_row
from reactionmenu import ViewButton, ViewMenu


class Tour(commands.Cog):
    """Collection of commands for looking up the various tours Bruce has done."""

    def __init__(self, bot: commands.Bot) -> None:
        """Init Tour cog with bot."""
        self.bot = bot
        self.description = "Bruce's various tours."
        self.thumbpath = Path(Path(__file__).parents[2], "images", "tours")

    async def default_tour_embed(
        self,
        ctx: commands.Context,
        cur: psycopg.AsyncCursor,
    ) -> None:
        """Embed to send if no argument is provided. Gets all tours."""
        menu = ViewMenu(
            ctx,
            menu_type=ViewMenu.TypeEmbedDynamic,
            rows_requested=4,
            all_can_click=True,
            timeout=None,
        )

        res = await cur.execute(
            """
            WITH "event_info" AS (
                SELECT
                    event_id,
                    event_date,
                    brucebase_url
                FROM "events"
            )
            SELECT
                "tours".*,
                (SELECT event_date AS first_date FROM "event_info"
                    WHERE event_id = "tours"."first_show"),
                (SELECT brucebase_url AS first_url FROM "event_info"
                    WHERE event_id = "tours"."first_show"),
                (SELECT event_date AS last_date FROM "event_info"
                    WHERE event_id = "tours"."last_show"),
                (SELECT brucebase_url AS last_url FROM "event_info"
                    WHERE event_id = "tours"."last_show")
            FROM "tours"
            ORDER BY first_show ASC;""",
        )

        tours = await res.fetchall()

        for row in tours:
            tour_shows_url = (
                f"http://brucebase.wikidot.com/stats:shows-{row["brucebase_id"]}"
            )
            tour_songs_url = (
                f"http://brucebase.wikidot.com/stats:songs-{row["brucebase_id"]}"
            )
            shows = f"Shows: [{row['num_shows']}]({tour_shows_url})"
            songs = f"Songs: [{row['num_songs']}]({tour_songs_url})"
            first_show = f"First Show: [{row['first_date']}](http://brucebase.wikidot.com{row['first_url']})"
            last_show = f"Last Show: [{row['last_date']}](http://brucebase.wikidot.com{row['last_url']})"

            tour = f"### **{row['tour_name']}**\n- {shows}\n- {songs}\n- {first_show}\n- {last_show}"  # noqa: E501
            menu.add_row(tour)

        menu.add_button(ViewButton.back())
        menu.add_button(ViewButton.next())
        await menu.start()

    async def get_tour_info(
        self,
        tour_id: str,
        cur: psycopg.AsyncCursor,
    ) -> dict:
        """Get info with given tour_id."""
        res = await cur.execute(
            """SELECT
                t.*,
                e.event_date AS first_date,
                e.event_url AS first_url,
                e.city || ', ' ||
                coalesce(e.state, e.country) AS first_loc,
                e1.event_date AS last_date,
                e1.event_url AS last_url,
                e1.city || ', ' ||
                coalesce(e1.state, e1.country) AS last_loc
            FROM "tours" t
            LEFT JOIN "events_with_info" e ON e.event_id = t.first_show
            LEFT JOIN "events_with_info" e1 ON e1.event_id = t.last_show
            WHERE t.brucebase_id = %s""",
            (tour_id,),
        )

        return await res.fetchone()

    async def tour_embed(
        self,
        tour: dict,
        ctx: commands.Context,
    ) -> discord.Embed:
        """Create the song embed and sending."""
        tour_shows_url = (
            f"http://brucebase.wikidot.com/stats:shows-{tour["brucebase_id"]}"
        )
        tour_songs_url = (
            f"http://brucebase.wikidot.com/stats:songs-{tour["brucebase_id"]}"
        )

        thumbnail = f"{tour['brucebase_id']}.jpg"

        embed = await bot_embed.create_embed(
            ctx,
            tour["tour_name"],
            "",
            f"http://brucebase.wikidot.com/tour:{tour["brucebase_id"]}",
        )

        if Path(self.thumbpath, thumbnail).exists():
            file = discord.File(
                Path(self.thumbpath, thumbnail),
                filename=thumbnail,
            )

            embed.set_thumbnail(url=f"attachment://{thumbnail}")

        embed.add_field(
            name="Shows:",
            value=f"[{tour['num_shows']}]({tour_shows_url})",
            inline=False,
        )

        embed.add_field(
            name="Songs:",
            value=f"[{tour['num_songs']}]({tour_songs_url})",
            inline=False,
        )

        embed.add_field(
            name="First Show:",
            value=f"[{tour['first_date']} - {tour['first_loc']}]({tour['first_url']})",
            inline=False,
        )

        embed.add_field(
            name="Last Show:",
            value=f"[{tour['last_date']} - {tour['last_loc']}]({tour['last_url']})",
            inline=False,
        )

        try:
            await ctx.send(file=file, embed=embed)
        except UnboundLocalError:
            await ctx.send(embed=embed)

    @commands.command(name="tour", aliases=["t"])
    async def tour_find(
        self,
        ctx: commands.Context,
        *,
        tour: str = "",
    ) -> None:
        """Find tour based on input."""
        async with await db.create_pool() as pool:
            await pool.open()

            await ctx.typing()

            async with pool.connection() as conn, conn.cursor(
                row_factory=dict_row,
            ) as cur:
                if tour == "":
                    await self.default_tour_embed(ctx, cur)
                else:
                    res = await cur.execute(
                        """
                        SELECT
                            t.brucebase_id
                        FROM
                            "tours" t,
                            plainto_tsquery('english', %(query)s) query
                        WHERE query @@ fts
                        ORDER BY t.num_shows DESC NULLS LAST;
                        """,
                        {"query": tour},
                    )

                    tours = await res.fetchone()

                    if tours:
                        tour_info = await self.get_tour_info(tours["brucebase_id"], cur)
                        await self.tour_embed(tour_info, ctx)
                    else:
                        embed = await bot_embed.not_found_embed(
                            command=self.__class__.__name__,
                            message=tour,
                        )
                        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """Load extension into bot."""
    await bot.add_cog(Tour(bot))
