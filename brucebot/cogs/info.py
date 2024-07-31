from cogs.bot_stuff import bot_embed, db
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
                    count(distinct b.brucebase_url) AS band_count,
                    count(distinct e.event_id) AS event_count,
                    count(distinct r.brucebase_url) AS people_count,
                    count(distinct s.event_id) AS setlist_count,
                    count(distinct s1.brucebase_url) AS song_count,
                    count(distinct v.brucebase_url) AS venue_count
                FROM
                    events e
                LEFT JOIN setlists s ON s.event_id = e.event_id
                LEFT JOIN songs s1 ON s1.brucebase_url = s.song_id
                LEFT JOIN venues v ON v.brucebase_url = e.venue_id
                LEFT JOIN relations r ON r.first_appearance = e.event_id
                LEFT JOIN bands b ON b.first_appearance = e.event_id
                """,
            )

            return await res.fetchall()

    @commands.command(name="info")
    async def get_info(
        self,
        ctx: commands.Context,
    ) -> None:
        """Get info on bot and stats about database."""
        async with await db.create_pool() as pool:
            await ctx.typing()

            db_counts = await self.db_stats(pool)

            info_embed = await bot_embed.create_embed(
                ctx,
                title="Brucebot v2.0",
                description="A Discord bot to get info on Bruce Springsteen's performing history",
                url="",
            )


async def setup(bot: commands.Bot) -> None:
    """Load extension into bot."""
    await bot.add_cog(Info(bot))
