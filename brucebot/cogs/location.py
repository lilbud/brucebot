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
        argument: str = "",
    ) -> None:
        """Search for a city with a Bruce history.

        Cities can be found by either name or nickname/alias (NYC/Philly/etc.)
        """
        if argument == "":
            await ctx.send_help(ctx.command)
            return

        async with await db.create_pool() as pool:
            await ctx.typing()

            async with pool.connection() as conn, conn.cursor(
                row_factory=dict_row,
            ) as cur:
                res = await cur.execute(
                    """
                    SELECT
                        "cities".*,
                        (SELECT CONCAT('[', event_date, ']') ||
                            CONCAT('(', event_url, ')')
                            FROM "events_with_info" WHERE city="cities"."name"
                            AND event_date::date < current_date
                            ORDER BY event_date LIMIT 1) AS first_event,
                        (SELECT CONCAT('[', event_date, ']') ||
                            CONCAT('(', event_url, ')')
                            FROM "events_with_info" WHERE city="cities"."name"
                            AND event_date::date < current_date
                            ORDER BY event_date DESC LIMIT 1) AS last_event
                    FROM
                        "cities",
                        plainto_tsquery('english', %(query)s) query,
                        ts_rank(fts, query) rank,
                        SIMILARITY(%(query)s,
                            coalesce(aliases, unaccent(name), '')) similarity
                    WHERE query @@ fts
                    ORDER BY rank, similarity DESC NULLS LAST
                    """,
                    {"query": argument},
                )

                city = await res.fetchone()

            if city:
                await self.location_embed(location=city, ctx=ctx)
            else:
                embed = await bot_embed.not_found_embed(
                    command="city",
                    message=argument,
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
        argument: str = "",
    ) -> None:
        """Search for a state with a Bruce history.

        States can be found by either name or abbreviation.
        """
        if argument == "":
            await ctx.send_help(ctx.command)
            return

        async with await db.create_pool() as pool:
            await ctx.typing()

            async with pool.connection() as conn, conn.cursor(
                row_factory=dict_row,
            ) as cur:
                res = await cur.execute(
                    """
                    SELECT
                        "states"."state_abbrev",
                        "states"."state_name" AS name,
                        "states"."state_country" AS country,
                        "states"."num_events",
                        (SELECT CONCAT('[', event_date, ']') ||
                            CONCAT('(', event_url, ')')
                            FROM "events_with_info" WHERE state="states"."state_abbrev"
                            AND event_date::date < current_date
                            ORDER BY event_date LIMIT 1) AS first_event,
                        (SELECT CONCAT('[', event_date, ']') ||
                            CONCAT('(', event_url, ')')
                            FROM "events_with_info" WHERE state="states"."state_abbrev"
                            AND event_date::date < current_date
                            ORDER BY event_date DESC LIMIT 1) AS last_event
                    FROM
                        "states",
                        plainto_tsquery('english', %(query)s) query,
                        ts_rank(fts, query) rank,
                        SIMILARITY(%(query)s,
                            state_name || ' ' || state_abbrev) similarity
                    WHERE query @@ fts
                    ORDER BY rank, similarity DESC NULLS LAST
                    """,
                    {"query": argument},
                )

                state = await res.fetchone()

            if state:
                await self.location_embed(location=state, ctx=ctx)
            else:
                embed = await bot_embed.not_found_embed(
                    command="state",
                    message=argument,
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
        argument: str = "",
    ) -> None:
        """Search for a country with a Bruce history.

        Countries can be found by either name or abbreviation.
        """
        if argument == "":
            await ctx.send_help(ctx.command)
            return

        async with await db.create_pool() as pool:
            await ctx.typing()

            async with pool.connection() as conn, conn.cursor(
                row_factory=dict_row,
            ) as cur:
                res = await cur.execute(
                    """
                    SELECT
                        "countries".*,
                        (SELECT CONCAT('[', event_date, ']') ||
                            CONCAT('(', event_url, ')')
                            FROM "events_with_info" WHERE country="countries"."name"
                            AND event_date::date < current_date
                            ORDER BY event_date LIMIT 1) AS first_event,
                        (SELECT CONCAT('[', event_date, ']') ||
                            CONCAT('(', event_url, ')')
                            FROM "events_with_info" WHERE country="countries"."name"
                            AND event_date::date < current_date
                            ORDER BY event_date DESC LIMIT 1) AS last_event,
                        rank,
                        similarity
                    FROM
                        "countries",
                        plainto_tsquery('english', %(query)s) query,
                        ts_rank(fts, query) rank,
                        SIMILARITY(%(query)s, unaccent("countries"."name")) similarity
                    WHERE query @@ fts
                    ORDER BY rank, similarity DESC NULLS LAST
                    """,
                    {"query": argument},
                )

                country = await res.fetchone()

            if country:
                await self.location_embed(location=country, ctx=ctx)
            else:
                embed = await bot_embed.not_found_embed(
                    command="country",
                    message=argument,
                )
                await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """Load extension into bot."""
    await bot.add_cog(Location(bot))
