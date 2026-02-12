import discord
import psycopg
from cogs.bot_stuff import bot_embed, db
from discord.ext import commands
from psycopg.rows import dict_row


class Venue(commands.Cog):
    """Collection of commands for searching venues."""

    def __init__(self, bot: commands.Bot) -> None:
        """Init Album cog with bot."""
        self.bot = bot
        self.description = "Find venues with a Bruce history."

    async def venue_embed(
        self,
        venue: dict,
        ctx: commands.Context,
    ) -> discord.Embed:
        """Create the venue embed and sending."""
        embed = await bot_embed.create_embed(
            ctx=ctx,
            title=venue["full_location"],
            description=f"**Nicknames:** {venue['aliases']}",
            url=f"https://www.databruce.com/venues/{venue['id']}",
        )

        embed.add_field(name="Appearances", value=venue["event_count"])

        embed.add_field(
            name="First Event:",
            value=f"[{venue['first_event_date']}](https://www.databruce.com/events/{venue['first_event_id']})",
        )

        embed.add_field(
            name="Last Event:",
            value=f"[{venue['last_event_date']}](https://www.databruce.com/events/{venue['last_event_date']})",
        )

        return embed

    async def venue_search(self, query: str, cur: psycopg.AsyncCursor) -> dict:
        """Find best venue match using FTS."""
        res = await cur.execute(
            """
            WITH search_results AS (
                SELECT
                    v.*,
                    ts_rank_cd(v.tsv, websearch_to_tsquery('english', %(query)s)) AS fts_rank,
                    extensions.similarity(v.location, %(query)s) as typo_score,
                    log(v.event_count + 2) as pop_score,
                    websearch_to_tsquery('english', %(query)s) as q
                FROM
                    venues_text v
                WHERE
                    v.tsv @@ websearch_to_tsquery('english', %(query)s)
            )
            SELECT
                *
            FROM
                search_results sr
            ORDER BY
                sr.pop_score desc,
                extensions.SIMILARITY(%(query)s, sr.location) DESC,
                ts_rank(sr.tsv, q) DESC
            LIMIT 1;
            """,  # noqa: E501
            {"query": query},
        )

        return await res.fetchone()

    @commands.hybrid_command(
        name="venue",
        aliases=["v"],
        usage="<venue>",
        brief="Search database for venue.",
    )
    async def venue_find(
        self,
        ctx: commands.Context,
        *,
        venue_query: str,
    ) -> None:
        """Search database for venue.

        Venue can be found by name or alias.
        """
        async with (
            await db.create_pool() as pool,
            pool.connection() as conn,
            conn.cursor(
                row_factory=dict_row,
            ) as cur,
        ):
            venue = await self.venue_search(venue_query, cur)

            if venue is not None:
                embed = await self.venue_embed(venue, ctx)

                await ctx.send(embed=embed)
            else:
                embed = await bot_embed.not_found_embed(
                    command=self.__class__.__name__,
                    message=venue_query,
                )
                await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """Load extension into bot."""
    await bot.add_cog(Venue(bot))
