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
                t.id,
                t.brucebase_id,
                t.tour_name,
                t.num_shows,
                t.num_songs,
                coalesce(e.event_date::text, e.event_id) AS first_date,
                coalesce(e1.event_date::text, e1.event_id) AS last_date,
                v.formatted_loc AS first_loc,
                v1.formatted_loc AS last_loc
            FROM tours t
            LEFT JOIN events e ON e.event_id = t.first_show
            LEFT JOIN events e1 ON e1.event_id = t.last_show
            LEFT JOIN venues_text v ON v.id = e.venue_id
            LEFT JOIN venues_text v1 ON v1.id = e1.venue_id
            ORDER BY t.first_show
            """,
        )

        tours = await res.fetchall()

        for row in tours:
            shows = f"**Shows:** {row['num_shows']}"
            songs = f"**Songs:** {row['num_songs']}"
            first_show = f"**First:** {row['first_date']} - {row['first_loc']}"
            last_show = f"**Last:** {row['last_date']} - {row['last_loc']}"

            tour = f"### **{row['tour_name']}**\n- {shows}\t{songs}\n- {first_show}\n- {last_show}"  # noqa: E501
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
            """SELECT
                t.*,
                coalesce(e.event_date::text, e.event_id::text) AS first_date,
                e.event_id AS first_url,
                v.formatted_loc as first_loc,
                coalesce(e1.event_date::text, e1.event_id::text) AS last_date,
                e1.event_id AS last_url,
                v1.formatted_loc AS last_loc
            FROM "tours" t
            LEFT JOIN events e ON e.event_id = t.first_show
            LEFT JOIN events e1 ON e1.event_id = t.last_show
            LEFT JOIN venues_text v ON v.id = e.venue_id
            LEFT JOIN venues_text v1 ON v1.id = e1.venue_id
            WHERE t.id = %s""",
            (tour_id,),
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
            value=f"{tour['first_date']} - {tour['first_loc']}",
            inline=False,
        )

        embed.add_field(
            name="Last Show:",
            value=f"{tour['last_date']} - {tour['last_loc']}",
            inline=True,
        )

        shows_button = discord.ui.Button(
            style="link",
            url=f"http://brucebase.wikidot.com/stats:shows-{tour['brucebase_id']}",
            label="Shows on Tour",
            row=1,
        )

        songs_button = discord.ui.Button(
            style="link",
            url=f"http://brucebase.wikidot.com/stats:songs-{tour['brucebase_id']}",
            label="Songs Played on Tour",
            row=1,
        )

        first_show_button = discord.ui.Button(
            style="link",
            url=f"https://www.databruce.com/events/{tour['first_url']}",
            label="First Show",
            row=2,
        )

        last_show_button = discord.ui.Button(
            style="link",
            url=f"https://www.databruce.com/events/{tour['last_url']}",
            label="Last Show",
            row=2,
        )

        # view.add_item(item=shows_button)
        # view.add_item(item=songs_button)
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
                        SELECT
                            t.id
                        FROM
                            "tours" t,
                            "to_tsvector"('"english"'::"regconfig", (((((("brucebase_id" || ' '::"text") || "tour_name") || ' '::"text") || "substr"("first_show", 3)) || ' '::"text") || "substr"("last_show", 3))) fts,
                            plainto_tsquery('english', %(query)s) query
                        WHERE query @@ fts
                        ORDER BY t.num_shows DESC NULLS LAST;
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
