import ftfy
from cogs.bot_stuff import bot_embed, db
from discord.ext import commands
from psycopg.rows import dict_row


class Location(commands.Cog):
    """Collection of commands for searching different locations with a Bruce history."""

    def __init__(self, bot: commands.Bot) -> None:
        """Init Location cog with bot."""
        self.bot = bot
        self.description = "Find locations with a Bruce history"

    async def not_found_embed(
        self,
        ctx: commands.Context,
        location: str,
        query: str,
    ) -> None:
        """Embed if no locations found for the given date."""
        embed = await bot_embed.create_embed(
            ctx=ctx,
            description=f"No {location} found for `{query}`",
        )

        await ctx.send(embed=embed)

    async def location_embed(
        self,
        location: dict,
        ctx: commands.Context,
    ) -> None:
        """Embed for city."""
        embed = await bot_embed.create_embed(ctx=ctx, title=location["name"])

        embed.add_field(name="Num Events:", value=location["num_events"])
        embed.add_field(name="First:", value=location["first_event"])
        embed.add_field(name="Last:", value=location["last_event"])

        await ctx.send(embed=embed)

    @commands.group(
        name="location",
        aliases=["loc"],
        usage="[subcommand]",
        brief="Commands for finding locations with a Bruce history.",
    )
    async def location(self, ctx: commands.Context) -> None:
        """Find Location."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @location.command(
        name="city",
        usage="<city>",
        brief="Search for a city with a Bruce history.",
    )
    async def city_find(
        self,
        ctx: commands.Context,
        *,
        city_query: str,
    ) -> None:
        """Search for a city with a Bruce history.

        Cities can be found by either name or nickname/alias (NYC/Philly/etc.)
        """
        city_query = ftfy.fix_text(city_query)

        async with await db.create_pool() as pool:
            await ctx.typing()

            async with pool.connection() as conn, conn.cursor(
                row_factory=dict_row,
            ) as cur:
                res = await cur.execute(
                    """
                        SELECT
                            id,
                            name,
                            state_abbrev,
                            state_name,
                            aliases,
                            num_events,
                            '[' || first_date || '](http://brucebase.wikidot.com' ||
                                first_url || ')' AS first_event,
                            '[' || last_date || '](http://brucebase.wikidot.com' ||
                                last_url || ')' AS last_event
                        FROM
                            city_search,
                            plainto_tsquery('english', %(query)s) query,
                            to_tsvector('english', name || ' ' || state_abbrev || ' ' ||
                                state_name || ' ' || coalesce(aliases, '')) fts,
                            ts_rank(fts, query) rank,
                            similarity(name || ' ' || state_abbrev || ' ' || state_name
                                || ' ' || coalesce(aliases, ''), %(query)s) similarity
                        WHERE query @@ fts
                        ORDER BY similarity DESC, rank DESC NULLS LAST;
                    """,
                    {"query": city_query},
                )

                city = await res.fetchone()

            if city:
                await self.location_embed(location=city, ctx=ctx)
            else:
                embed = await bot_embed.not_found_embed(
                    command="city",
                    message=city_query,
                )
                await ctx.send(embed=embed)

    @location.command(
        name="state",
        usage="<state>",
        brief="Search for a state with a Bruce history.",
    )
    async def state_find(
        self,
        ctx: commands.Context,
        *,
        state_query: str,
    ) -> None:
        """Search for a state with a Bruce history.

        States can be found by either name or abbreviation.
        """
        async with await db.create_pool() as pool:
            await ctx.typing()

            async with pool.connection() as conn, conn.cursor(
                row_factory=dict_row,
            ) as cur:
                res = await cur.execute(
                    """
                        SELECT
                            state_name || ', ' || country AS name,
                            num_events,
                            '[' || first_date || '](http://brucebase.wikidot.com' ||
                                first_url || ')' AS first_event,
                            '[' || last_date || '](http://brucebase.wikidot.com' ||
                                last_url || ')' AS last_event
                        FROM
                            state_search,
                            plainto_tsquery('english', %(query)s) query,
                            to_tsvector('english', state_name || ' ' || state_abbrev
                                || ' ' || country) fts,
                            ts_rank(fts, query) rank,
                            similarity(state_name || ' ' || state_abbrev || ' ' ||
                                country, %(query)s) similarity
                        WHERE query @@ fts
                        ORDER BY similarity DESC, rank DESC;
                    """,
                    {"query": state_query},
                )

                state = await res.fetchone()

            if state:
                await self.location_embed(location=state, ctx=ctx)
            else:
                embed = await bot_embed.not_found_embed(
                    command="state",
                    message=state_query,
                )
                await ctx.send(embed=embed)

    @location.command(
        name="country",
        usage="<country>",
        brief="Search for a country with a Bruce history.",
    )
    async def country_find(
        self,
        ctx: commands.Context,
        *,
        country_query: str,
    ) -> None:
        """Search for a country with a Bruce history.

        Countries can be found by either name or abbreviation.
        """
        async with await db.create_pool() as pool:
            await ctx.typing()

            async with pool.connection() as conn, conn.cursor(
                row_factory=dict_row,
            ) as cur:
                res = await cur.execute(
                    """
                    SELECT
                        name,
                        num_events,
                        '[' || first_date || '](http://brucebase.wikidot.com' ||
                            first_url || ')' AS first_event,
                        '[' || last_date || '](http://brucebase.wikidot.com' ||
                            last_url || ')' AS last_event
                    FROM
                        country_search,
                        plainto_tsquery('english', %(query)s) query,
                        to_tsvector('english', name || ' ' || alpha_2 || ' ' || alpha_3
                            || coalesce(aliases, '')) fts,
                        ts_rank(fts, query) rank,
                        similarity(name || ' ' || alpha_2 || ' ' || alpha_3 ||
                            coalesce(aliases, ''), %(query)s) similarity
                    WHERE query @@ fts
                    ORDER BY similarity DESC, rank DESC;
                    """,
                    {"query": country_query},
                )

                country = await res.fetchone()

            if country:
                await self.location_embed(location=country, ctx=ctx)
            else:
                embed = await bot_embed.not_found_embed(
                    command="country",
                    message=country_query,
                )
                await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """Load extension into bot."""
    await bot.add_cog(Location(bot))
