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

    @commands.hybrid_group(
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
    )
    async def city_find(
        self,
        ctx: commands.Context,
        *,
        city: str,
    ) -> None:
        """Search for a city with a Bruce history.

        Cities can be found by either name or nickname/alias (NYC/Philly/etc.)
        """
        city = ftfy.fix_text(city)

        async with (
            await db.create_pool() as pool,
            pool.connection() as conn,
            conn.cursor(
                row_factory=dict_row,
            ) as cur,
        ):
            res = await cur.execute(
                """
                    WITH cities_fts AS (
                        SELECT
                            c.id,
                            c.name AS city_name,
                            s.name AS state_name,
                            c.name || ', ' || s.state_abbrev AS name,
                            s.state_abbrev,
                            c.aliases,
                            '[' || e.event_date ||
                                '](http://brucebase.wikidot.com' ||
                                e.brucebase_url || ')' AS first_event,
                            '[' || e1.event_date ||
                                '](http://brucebase.wikidot.com' ||
                                e1.brucebase_url || ')' AS last_event,
                            c.num_events
                            FROM cities c
                        LEFT JOIN states s ON s.id = c.state
                        LEFT JOIN events e ON e.event_id = c.first_played
                        LEFT JOIN events e1 ON e1.event_id = c.last_played
                    )
                    SELECT
                        *
                    FROM
                        cities_fts,
                        plainto_tsquery('english', %(query)s) query,
                        to_tsvector('english', city_name || ' ' || state_name || ' '
                            || state_abbrev || ' ' || coalesce(aliases, '')) fts,
                        ts_rank(fts, query) rank,
                        extensions.SIMILARITY(city_name || ' ' || state_name || ' ' ||
                            state_abbrev || ' ' ||
                            coalesce(aliases, ''), %(query)s) similarity
                    WHERE query @@ fts
                    ORDER BY similarity DESC, rank DESC NULLS LAST;
                """,
                {"query": city},
            )

            city = await res.fetchone()

        if city:
            await self.location_embed(location=city, ctx=ctx)
        else:
            embed = await bot_embed.not_found_embed(
                command="city",
                message=city,
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
        state: str,
    ) -> None:
        """Search for a state with a Bruce history.

        States can be found by either name or abbreviation.
        """
        async with await db.create_pool() as pool:
            async with (
                pool.connection() as conn,
                conn.cursor(
                    row_factory=dict_row,
                ) as cur,
            ):
                res = await cur.execute(
                    """
                        WITH states_fts AS (
                            SELECT
                                s.name || ', ' || c.name AS name,
                                s.name AS state_name,
                                s.state_abbrev,
                                c.name AS country,
                                '[' || e.event_date ||
                                    '](http://brucebase.wikidot.com' ||
                                    e.brucebase_url || ')' AS first_event,
                                '[' || e1.event_date ||
                                    '](http://brucebase.wikidot.com' ||
                                    e1.brucebase_url || ')' AS last_event,
                                s.num_events
                                FROM states s
                            LEFT JOIN countries c ON c.id = s.country
                            LEFT JOIN events e ON e.event_id = c.first_played
                            LEFT JOIN events e1 ON e1.event_id = c.last_played
                        )
                        SELECT
                            *
                        FROM
                            states_fts,
                            plainto_tsquery('english', %(query)s) query,
                            to_tsvector('english', state_name || ' ' || state_abbrev ||
                                ' ' || country) fts,
                            ts_rank(fts, query) rank,
                            extensions.SIMILARITY(state_name || ' ' || state_abbrev ||
                                ' ' || country, %(query)s) similarity
                        WHERE query @@ fts
                        ORDER BY similarity DESC, rank DESC NULLS LAST;
                    """,
                    {"query": state},
                )

                state = await res.fetchone()

            if state:
                await self.location_embed(location=state, ctx=ctx)
            else:
                embed = await bot_embed.not_found_embed(
                    command="state",
                    message=state,
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
        country: str,
    ) -> None:
        """Search for a country with a Bruce history.

        Countries can be found by either name or abbreviation.
        """
        async with await db.create_pool() as pool:
            async with (
                pool.connection() as conn,
                conn.cursor(
                    row_factory=dict_row,
                ) as cur,
            ):
                res = await cur.execute(
                    """
                    WITH states_fts AS (
                        SELECT
                            c.name,
                            c.num_events,
                            c.alpha_2,
                            c.alpha_3,
                            c.aliases,
                            '[' || e.event_date ||
                                '](http://brucebase.wikidot.com' ||
                                e.brucebase_url || ')' AS first_event,
                            '[' || e1.event_date ||
                                '](http://brucebase.wikidot.com' ||
                                e1.brucebase_url || ')' AS last_event
                            FROM countries c
                        LEFT JOIN events e ON e.event_id = c.first_played
                        LEFT JOIN events e1 ON e1.event_id = c.last_played
                    )
                    SELECT
                        *
                    FROM
                        states_fts,
                        plainto_tsquery('english', %(query)s) query,
                        to_tsvector('english', name || ' ' || alpha_2 || ' ' ||
                            alpha_3 || coalesce(aliases, '')) fts,
                        ts_rank(fts, query) rank,
                        extensions.SIMILARITY(name || ' ' || alpha_2 || ' ' || alpha_3 ||
                            coalesce(aliases, ''), %(query)s) similarity
                    WHERE query @@ fts
                    ORDER BY similarity DESC, rank DESC NULLS LAST;
                    """,
                    {"query": country},
                )

                country = await res.fetchone()

            if country:
                await self.location_embed(location=country, ctx=ctx)
            else:
                embed = await bot_embed.not_found_embed(
                    command="country",
                    message=country,
                )
                await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """Load extension into bot."""
    await bot.add_cog(Location(bot))
