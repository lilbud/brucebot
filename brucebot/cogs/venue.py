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
        stats: dict,
        ctx: commands.Context,
    ) -> discord.Embed:
        """Create the venue embed and sending."""
        embed = await bot_embed.create_embed(
            ctx=ctx,
            title=venue["formatted_loc"],
            description=f"**Nicknames:** {venue['aliases']}",
            url=f"https://www.databruce.com/venues/{venue['id']}",
        )

        embed.add_field(name="Appearances", value=venue["num_events"])

        embed.add_field(
            name="First Event:",
            value=f"[{stats['first']['event_date']}](https://www.databruce.com/events/{stats['first']['event_id']})",
        )

        embed.add_field(
            name="Last Event:",
            value=f"[{stats['last']['event_date']}](https://www.databruce.com/events/{stats['last']['event_id']})",
        )

        return embed

    async def venue_stats(self, venue_id: id, cur: psycopg.AsyncCursor) -> dict:
        """Get stats for the given venue."""
        res = await cur.execute(
            """
            SELECT
                coalesce(e.event_date::text, e.event_id) as event_date,
                e.event_id
            FROM events e
            WHERE e.venue_id = %(query)s
            ORDER BY e.event_date
            """,
            {"query": venue_id},
        )

        stats = await res.fetchall()
        return {"first": stats[0], "last": stats[-1]}

    async def venue_search(self, query: str, cur: psycopg.AsyncCursor) -> dict:
        """Find best venue match using FTS."""
        res = await cur.execute(
            """
            SELECT
                *
            FROM
                venues_text v
                left join venues v1 ON v1.id = v.id,
                plainto_tsquery('english', %(query)s) query,
                to_tsvector('english', v.name || ' ' || v.location || ' ' ||
                    coalesce(v1.aliases, '')) fts,
                ts_rank(fts, query) rank,
                extensions.similarity(v.name || ' ' || v.location || ' ' ||
                    coalesce(v1.aliases, ''), %(query)s) similarity
            WHERE query @@ fts
            ORDER BY similarity DESC, rank DESC;
            """,
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
                stats = await self.venue_stats(venue["id"], cur)

                embed = await self.venue_embed(venue, stats, ctx)

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
