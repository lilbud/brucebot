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

    async def default_tour_embed(
        self,
        ctx: commands.Context,
        cur: psycopg.AsyncCursor,
    ) -> None:
        """Embed to send if no argument is provided. Gets all tours."""
        menu = ViewMenu(
            ctx,
            menu_type=ViewMenu.TypeEmbedDynamic,
            rows_requested=5,
            all_can_click=True,
            timeout=None,
        )

        res = await cur.execute(
            """
            SELECT
                t.*,
                coalesce(e.event_date::text, e.event_id) AS first_event_date,
                e.event_id AS first_event_id,
                coalesce(e1.event_date::text, e1.event_id) AS last_event_date,
                e1.event_id AS last_event_id
            FROM "tours" t
            LEFT JOIN events e ON e.id = t.first_event
            LEFT JOIN events e1 ON e1.id = t.last_event
            ORDER BY e.event_id
            """,
        )

        tours = await res.fetchall()

        for row in tours:
            shows = f"**Shows:** {row['num_shows']}"
            songs = f"**Songs:** {row['num_songs']}"
            first_show = f"**First:** [{row['first_event_date']}](https://www.databruce.com/events/{row['first_event_id']})"
            last_show = f"**Last:** [{row['last_event_date']}](https://www.databruce.com/events/{row['last_event_id']})"

            tour = f"### **[{row['tour_name']}](https://www.databruce.com/tours/{row['id']})**\n- {shows}\t{songs}\n- {first_show}\n- {last_show}"  # noqa: E501
            menu.add_row(tour)

        menu.add_button(ViewButton.back())
        menu.add_button(ViewButton.next())
        await menu.start()

    async def get_tour_info(
        self,
        tour_id: int,
        cur: psycopg.AsyncCursor,
    ) -> dict:
        """Get info with given tour_id."""
        res = await cur.execute(
            """
            SELECT
                t.*,
                coalesce(e.event_date::text, e.event_id) AS first_event_date,
                e.event_id AS first_event_id,
                coalesce(e1.event_date::text, e1.event_id) AS last_event_date,
                e1.event_id AS last_event_id
            FROM "tours" t
            LEFT JOIN events e ON e.id = t.first_event
            LEFT JOIN events e1 ON e1.id = t.last_event
            WHERE t.id = %(tour_id)s
            """,
            {"tour_id": tour_id},
        )

        return await res.fetchone()

    async def tour_embed(
        self,
        tour: dict,
        ctx: commands.Context,
    ) -> discord.Embed:
        """Create the song embed and sending."""
        view = discord.ui.View()

        embed = await bot_embed.create_embed(
            ctx,
            tour["tour_name"],
            "",
            f"https://www.databruce.com/tours/{tour['id']}",
        )

        thumbnail = f"https://raw.githubusercontent.com/lilbud/brucebot/main/images/tours/{tour['brucebase_tag']}.jpg"
        embed.set_thumbnail(url=thumbnail)

        embed.add_field(
            name="Shows:",
            value=f"{tour['num_shows']}",
            inline=True,
        )

        embed.add_field(
            name="Songs:",
            value=f"{tour['num_songs']}",
            inline=True,
        )

        embed.add_field(
            name="First Show:",
            value=f"[{tour['first_event_date']}](https://www.databruce.com/events/{tour['first_event_id']})",
            inline=False,
        )

        embed.add_field(
            name="Last Show:",
            value=f"[{tour['last_event_date']}](https://www.databruce.com/events/{tour['last_event_id']})",
            inline=True,
        )

        first_show_button = discord.ui.Button(
            style="link",
            url=f"https://www.databruce.com/events/{tour['first_event_id']}",
            label="First Show",
            row=2,
        )

        last_show_button = discord.ui.Button(
            style="link",
            url=f"https://www.databruce.com/events/{tour['last_event_id']}",
            label="Last Show",
            row=2,
        )

        view.add_item(item=first_show_button)
        view.add_item(item=last_show_button)

        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="tour", aliases=["t"])
    async def tour_find(
        self,
        ctx: commands.Context,
        *,
        tour: str = "",
    ) -> None:
        """Find tour based on input."""
        async with (
            await db.create_pool() as pool,
            pool.connection() as conn,
            conn.cursor(
                row_factory=dict_row,
            ) as cur,
        ):
            if tour == "":
                await self.default_tour_embed(ctx, cur)
            else:
                res = await cur.execute(
                    """
                        WITH search_results AS (
                            SELECT
                                t.*,
                                websearch_to_tsquery('english', %(query)s) AS q
                            FROM
                                tours t
                            WHERE
                                t.fts_name_vector @@ websearch_to_tsquery('english', %(query)s)
                        )
                        SELECT
                            *
                        FROM
                            search_results sr
                        ORDER BY
                            num_shows desc,
                            extensions.SIMILARITY(%(query)s, sr.tour_name) DESC,
                            ts_rank(sr.fts_name_vector, q) DESC
                        LIMIT 1;
                        """,  # noqa: E501
                    {"query": tour},
                )

                tours = await res.fetchone()

                if tours:
                    tour_info = await self.get_tour_info(tours["id"], cur)
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
