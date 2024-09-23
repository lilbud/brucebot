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
            title=venue["name"],
            description=f"**Nicknames:** {venue["aliases"]}",
            url=f"http://brucebase.wikidot.com/venue:{venue["brucebase_url"]}",
        )

        embed.add_field(name="Location", value=venue["location"], inline=False)

        embed.add_field(name="Appearances", value=venue["num_events"])

        embed.add_field(
            name="First Event:",
            value=f"[{stats['first']["event_date"]}](http://brucebase.wikidot.com{stats['first']['brucebase_url']})",
        )

        embed.add_field(
            name="Last Event:",
            value=f"[{stats['last']["event_date"]}](http://brucebase.wikidot.com{stats['last']['brucebase_url']})",
        )

        return embed

    async def venue_stats(self, venue_id: str, cur: psycopg.AsyncCursor) -> dict:
        """Get stats for the given venue."""
        res = await cur.execute(
            """
            SELECT
                e.event_date,
                e.brucebase_url
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
                brucebase_url,
                name,
                city || ', ' ||
                coalesce(state, country) AS location,
                num_events,
                aliases
            FROM
                "venues" v,
                plainto_tsquery('english', %(query)s) query,
                ts_rank(fts, query) rank,
                SIMILARITY(%(query)s, name || ' ' || brucebase_url || ' ' ||
                    coalesce(aliases, '') || ' ' ||
                    coalesce(city, '')) similarity
            WHERE query @@ fts AND num_events > 0
            ORDER BY similarity DESC, rank DESC;
            """,
            {"query": query},
        )

        return await res.fetchone()

    @commands.command(
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
        async with await db.create_pool() as pool:
            await ctx.typing()

            async with pool.connection() as conn, conn.cursor(
                row_factory=dict_row,
            ) as cur:
                venue = await self.venue_search(venue_query, cur)

                if venue is not None:
                    stats = await self.venue_stats(venue["brucebase_url"], cur)

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
