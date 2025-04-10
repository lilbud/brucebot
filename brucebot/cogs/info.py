from cogs.bot_stuff import bot_embed, db, viewmenu
from discord.ext import commands
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool


class Info(commands.Cog):
    """Collection of commands for pulling setlists for different shows."""

    def __init__(self, bot: commands.Bot) -> None:
        """Init Setlist cog with bot."""
        self.bot = bot
        self.description = "Bot/Database Info"

    async def db_stats(self, pool: AsyncConnectionPool) -> dict:
        """Get latest stats on database."""
        async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            res = await cur.execute(
                """
                SELECT
                    count(distinct b.brucebase_url)  || ' bands' AS band_count,
                    count(distinct e.event_id)  || ' events' AS event_count,
                    count(distinct r.brucebase_url) || ' people' AS people_count,
                    count(distinct s.event_id)  || ' setlists' AS setlist_count,
                    count(distinct s1.brucebase_url) || ' songs' AS song_count,
                    count(distinct v.brucebase_url) || ' venues' AS venue_count,
                    (SELECT count(id) FROM bootlegs) || ' bootlegs' AS bootleg_count
                FROM
                    events e
                LEFT JOIN setlists s ON s.event_id = e.event_id
                LEFT JOIN songs s1 ON s1.id = s.song_id
                LEFT JOIN venues v ON v.id = e.venue_id
                LEFT JOIN relations r ON r.first_appearance = e.event_id
                LEFT JOIN bands b ON b.first_appearance = e.event_id
                """,
            )

            counts = await res.fetchone()

            return [
                f"- **{k.replace('_', ' ').title()}** - _{v}_"
                for k, v in counts.items()
            ]

    @commands.hybrid_command(name="status", description="Status message.")
    async def status(
        self,
        ctx: commands.Context,
    ) -> None:
        """Status message."""
        await ctx.send("There IS somebody alive out there.")

    @commands.hybrid_command(
        name="binfo",
        description="Get info on bot and stats about database.",
    )
    async def get_info(
        self,
        ctx: commands.Context,
    ) -> None:
        """Get info on bot and stats about database."""
        async with await db.create_pool() as pool:
            menu = await viewmenu.create_view_menu(
                ctx,
                style="Page $/&",
            )

            db_counts = await self.db_stats(pool)

            info_embed = await bot_embed.create_embed(
                ctx,
                title="Brucebot v2.0 Info",
                description="A Discord bot to get info on Bruce Springsteen's performing history, created by Lilbud.",  # noqa: E501
                url="https://github.com/lilbud/brucebot",
            )

            info_embed.set_footer(text="Go to next page for database stats")

            sources = [
                "- [Brucebase](http://brucebase.wikidot.com/): primary source of data (songs, setlists, etc.)",  # noqa: E501
                "- [SpringsteenLyrics](https://www.springsteenlyrics.com/index.php): primary source of Bootleg info.",  # noqa: E501
                "- [SpringsteenDVDs](https://springsteendvds.wordpress.com/): secondary bootleg info source (videos)",  # noqa: E501
                "- [Musicbrainz](https://musicbrainz.org/): info on releases/bootlegs",
            ]

            info_embed.add_field(
                name="History:",
                value="- Version 1.0: March 2023 - July 2024\n- Version 2.0: July 2024 - current",  # noqa: E501
                inline=False,
            )

            info_embed.add_field(name="Sources:", value="\n".join(sources))

            info_embed.add_field(
                name="Credits:",
                value="- [See Here for Credits List](https://github.com/lilbud/databruce/blob/main/CREDITS.md)",
                inline=False,
            )

            menu.add_page(embed=info_embed)

            counts_embed = await bot_embed.create_embed(
                ctx,
                title="Database Stats",
                description="\n".join(db_counts),
            )

            menu.add_page(embed=counts_embed)

            await menu.start()


async def setup(bot: commands.Bot) -> None:
    """Load extension into bot."""
    await bot.add_cog(Info(bot))
