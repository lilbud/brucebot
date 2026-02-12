import ftfy
from cogs.bot_stuff import bot_embed, db, utils
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

        first_event = await utils.format_link(
            url=f"https://databruce.com/events/{location['first_event']}",
            text=location["first_event_date"],
        )

        last_event = await utils.format_link(
            url=f"https://databruce.com/events/{location['last_event']}",
            text=location["last_event_date"],
        )

        embed.add_field(name="Num Events:", value=location["num_events"])
        embed.add_field(name="First:", value=first_event)
        embed.add_field(name="Last:", value=last_event)

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
                WITH search_results AS (
                    SELECT
                        CASE WHEN c1.id in (2,6,37) then concat_ws(', ', c.name, s.state_abbrev) else s.name end,
                        c.num_events,
                        e.event_date as first_event_date,
                        e.event_id as first_event,
                        e1.event_date as last_event_date,
                        e1.event_id as last_event,
                        c.fts_name_vector,
                        websearch_to_tsquery('english', %(query)s) AS q
                    FROM
                        cities c
                    left join states s on s.id = c.state
                    left join countries c1 on c1.id = s.country
                    LEFT JOIN events e ON e.id = s.first_event
                    LEFT JOIN events e1 ON e1.id = s.last_event
                    WHERE
                        c.fts_name_vector @@ websearch_to_tsquery('english', %(query)s)
                )
                SELECT
                    *
                FROM
                    search_results
                ORDER BY
                    extensions.SIMILARITY(%(query)s, name) DESC,
                    ts_rank(fts_name_vector, q) DESC
                LIMIT 1;
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
                    WITH search_results AS (
                        SELECT
                            CASE WHEN c1.id in (2,6,37) then concat_ws(', ', s.name, c1.name) else s.name end,
                            s.num_events,
                            e.event_date as first_event_date,
                            e.event_id as first_event,
                            e1.event_date as last_event_date,
                            e1.event_id as last_event,
                            s.fts_name_vector,
                            websearch_to_tsquery('english', 'pa') AS q
                        FROM
                            states s
                        left join countries c1 on c1.id = s.country
                        LEFT JOIN events e ON e.id = s.first_event
                        LEFT JOIN events e1 ON e1.id = s.last_event
                        WHERE
                            s.fts_name_vector @@ websearch_to_tsquery('english', 'pa')
                    )
                    SELECT
                        *
                    FROM
                        search_results
                    ORDER BY
                        extensions.SIMILARITY('pa', name) DESC,
                        ts_rank(fts_name_vector, q) DESC
                    LIMIT 1;
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
                    WITH search_results AS (
                        SELECT
                            c.name,
                            c.num_events,
                            coalesce(e.event_date::text, e.event_id) as first_event_date,
                            e.event_id as first_event,
                            coalesce(e1.event_date::text, e1.event_id) as last_event_date,
                            e1.event_id as last_event,
                            c.fts_name_vector,
                            websearch_to_tsquery('english', %(query)s) AS q
                        FROM
                            countries c
                        LEFT JOIN events e ON e.id = c.first_event
                        LEFT JOIN events e1 ON e1.id = c.last_event
                        WHERE
                            c.fts_name_vector @@ websearch_to_tsquery('english', %(query)s)
                    )
                    SELECT
                        *
                    FROM
                        search_results
                    ORDER BY
                        extensions.SIMILARITY(%(query)s, name) DESC,
                        ts_rank(fts_name_vector, q) DESC
                    LIMIT 1;
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
