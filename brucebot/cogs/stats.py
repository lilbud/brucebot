import ftfy
import psycopg
from cogs.bot_stuff import bot_embed, db, viewmenu
from discord.ext import commands
from psycopg.rows import dict_row


class Stats(commands.Cog):
    """Collection of commands for searching various live statistics."""

    def __init__(self, bot: commands.Bot) -> None:
        """Init Setlist cog with bot."""
        self.bot = bot
        self.description = "Stats about songs Bruce has played live."

    async def song_find_fuzzy(
        self,
        query: str,
        cur: psycopg.AsyncCursor,
    ) -> dict:
        """Fuzzy search SONGS table using full text search."""
        res = await cur.execute(
            """
            SELECT
                s.id,
                s.brucebase_url,
                s.song_name,
                rank,
                similarity
            FROM
                "songs" s,
                plainto_tsquery('simple', %(query)s) query,
                ts_rank(fts, query) rank,
                SIMILARITY(coalesce(aliases, '') || ' ' || coalesce(short_name, '') || ' ' || song_name, %(query)s) similarity
            WHERE query @@ fts
            AND similarity >= 0.0415
            ORDER BY similarity DESC, rank DESC;
            """,  # noqa: E501
            {"query": ftfy.fix_text(query)},
        )

        return await res.fetchall()

    async def get_tour_stats(
        self,
        cur: psycopg.AsyncCursor,
        tour_id: str,
        position: str,
    ) -> list[dict]:
        """Get opener/closer by tour_id."""
        res = await cur.execute(
            """SELECT
                s1.song_name,
                s.position,
                count(*) AS total
            FROM "setlists" s
            LEFT JOIN "events" e USING (event_id)
            LEFT JOIN "songs" s1 ON s1.id = s.song_id
            WHERE s.position = %(position)s
            AND e.tour_id = %(tour_id)s
            AND s.set_name = ANY(ARRAY['Show', 'Set 1', 'Set 2', 'Encore'])
            GROUP BY s1.song_name, s.position
            ORDER BY count(*) DESC
            """,
            {"position": position, "tour_id": tour_id},
        )

        return await res.fetchall()

    async def find_tour(
        self,
        cur: psycopg.AsyncCursor,
        tour_query: str,
    ) -> dict:
        """."""
        res = await cur.execute(
            """SELECT
                t.id,
                t.brucebase_id,
                t.tour_name
            FROM
                "tours" t,
                plainto_tsquery('english', %(tour)s) query
            WHERE query @@ fts
            ORDER BY t.id ASC NULLS LAST;""",
            {"tour": tour_query},
        )

        return await res.fetchone()

    @commands.group(
        name="opener",
        usage="[subcommand]",
        brief="Commands for show/set opener stats.",
    )
    async def opener(self, ctx: commands.Context) -> None:
        """Commands for show/set opener stats."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @commands.group(
        name="closer",
        usage="[subcommand]",
        brief="Commands for show/set closer stats.",
    )
    async def closer(self, ctx: commands.Context) -> None:
        """Commands for show/set opener stats."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @opener.command(name="song", usage="<song>")
    async def opener_stats(
        self,
        ctx: commands.Context,
        *,
        song: str,
    ) -> None:
        """Stats on when a song has closed a set/show."""
        async with await db.create_pool() as pool:
            await ctx.typing()

            async with (
                pool.connection() as conn,
                conn.cursor(
                    row_factory=dict_row,
                ) as cur,
            ):
                songs = await self.song_find_fuzzy(query=song, cur=cur)

                if len(songs) > 0:
                    res = await cur.execute(
                        """SELECT o.* FROM "openers_closers" o LEFT JOIN "setlists" s
                            ON s.position = o.position WHERE o.song_id=%s
                            AND o.position LIKE '%%Opener'
                            GROUP BY o.song_id, o.position, o.count
                            ORDER BY min(s.song_num::int) ASC;""",
                        (songs[0]["id"],),
                    )

                    openers_list = await res.fetchall()

                    if len(openers_list) > 0:
                        embed = await bot_embed.create_embed(
                            ctx,
                            title=songs[0]["song_name"],
                            url=f"http://brucebase.wikidot.com/song:{songs[0]['brucebase_url']}",
                        )

                        for i in openers_list:
                            embed.add_field(
                                name=i["position"],
                                value=i["count"],
                                inline=False,
                            )

                        await ctx.send(embed=embed)
                    else:
                        embed = await bot_embed.not_found_embed(
                            command="Stats",
                            message=f"Opener, Song: {song}",
                        )

                        await ctx.send(embed=embed)
                else:
                    embed = await bot_embed.not_found_embed(
                        command="Stats",
                        message=f"Opener, Song: {song}",
                    )

                    await ctx.send(embed=embed)

    @closer.command(name="song", usage="<song>")
    async def closer_stats(
        self,
        ctx: commands.Context,
        *,
        song: str,
    ) -> None:
        """Stats on when a song has closed a set/show."""
        async with await db.create_pool() as pool:
            await ctx.typing()

            async with (
                pool.connection() as conn,
                conn.cursor(
                    row_factory=dict_row,
                ) as cur,
            ):
                songs = await self.song_find_fuzzy(query=song, cur=cur)

                if songs != []:
                    res = await cur.execute(
                        """SELECT o.* FROM "openers_closers" o LEFT JOIN "setlists" s
                            ON s.position = o.position WHERE o.song_id=%s
                            AND o.position LIKE '%%Closer'
                            GROUP BY o.song_id, o.position, o.count
                            ORDER BY min(s.song_num::int) ASC;""",
                        (songs[0]["id"],),
                    )

                    closers_list = await res.fetchall()

                    if len(closers_list) > 0:
                        embed = await bot_embed.create_embed(
                            ctx,
                            title=songs[0]["song_name"],
                            url=f"http://brucebase.wikidot.com/song:{songs[0]['brucebase_url']}",
                        )

                        for i in closers_list:
                            embed.add_field(
                                name=i["position"],
                                value=i["count"],
                                inline=False,
                            )

                        await ctx.send(embed=embed)
                    else:
                        embed = await bot_embed.not_found_embed(
                            command="Stats",
                            message=f"Closer, Song: {song}",
                        )

                        await ctx.send(embed=embed)
                else:
                    embed = await bot_embed.not_found_embed(
                        command="Stats",
                        message=f"Closer, Song: {song}",
                    )

                    await ctx.send(embed=embed)

    @opener.command(name="tour", usage="<tour>")
    async def opener_tour_stats(
        self,
        ctx: commands.Context,
        *,
        tour_query: str,
    ) -> None:
        """Get list of show openers for given tour."""
        async with await db.create_pool() as pool:
            await ctx.typing()

            async with (
                pool.connection() as conn,
                conn.cursor(
                    row_factory=dict_row,
                ) as cur,
            ):
                tour = await self.find_tour(cur, tour_query)

                print(tour)

                if tour:
                    stats = await self.get_tour_stats(
                        cur,
                        tour_id=tour["id"],
                        position="Show Opener",
                    )

                    data = [
                        f"{index}. **{row['song_name']}** - *{row['total']} time(s)*"
                        for index, row in enumerate(stats)
                    ]
                    await viewmenu.stats_menu(
                        ctx=ctx,
                        data=data,
                        title=f"Top Openers For: {tour['tour_name']}",
                        rows=10,
                    )
                else:
                    embed = await bot_embed.not_found_embed(
                        command="Stats",
                        message=f"Opener, Tour: {tour_query}",
                    )

                    await ctx.send(embed=embed)

    @closer.command(name="tour", usage="<tour>")
    async def closer_tour_stats(
        self,
        ctx: commands.Context,
        *,
        tour_query: str,
    ) -> None:
        """Get list of closers by tour."""
        async with await db.create_pool() as pool:
            await ctx.typing()

            async with (
                pool.connection() as conn,
                conn.cursor(
                    row_factory=dict_row,
                ) as cur,
            ):
                tour = await self.find_tour(cur, tour_query)

                if tour:
                    stats = await self.get_tour_stats(
                        cur,
                        tour_id=tour["id"],
                        position="Show Closer",
                    )

                    data = [
                        f"{index}. **{row['song_name']}** - *{row['total']} time(s)*"
                        for index, row in enumerate(stats)
                    ]
                    await viewmenu.stats_menu(
                        ctx=ctx,
                        data=data,
                        title=f"Top Closers For: {tour['tour_name']}",
                        rows=10,
                    )
                else:
                    embed = await bot_embed.not_found_embed(
                        command="Stats",
                        message=f"Closer, Tour: {tour_query}",
                    )

                    await ctx.send(embed=embed)

    @opener.command(name="year", usage="<year>")
    async def opener_year_stats(
        self,
        ctx: commands.Context,
        *,
        year: str,
    ) -> None:
        """Get list of show openers for given year."""
        async with await db.create_pool() as pool:
            await ctx.typing()

            async with (
                pool.connection() as conn,
                conn.cursor(
                    row_factory=dict_row,
                ) as cur,
            ):
                res = await cur.execute(
                    """
                    SELECT
                        s1.song_name,
                        s.position,
                        count(*) AS total
                    FROM "setlists" s
                    LEFT JOIN "events" e USING (event_id)
                    LEFT JOIN "songs" s1 ON s1.id = s.song_id
                    WHERE s.position = 'Show Opener'
                    AND to_char(e.event_date, 'YYYY') = %s
                    GROUP BY s1.song_name, s.position
                    ORDER BY count(*) DESC
                    """,
                    (year,),
                )

                stats = await res.fetchall()

                if stats:
                    data = [
                        f"{index}. **{row['song_name']}** - *{row['total']} time(s)*"
                        for index, row in enumerate(stats)
                    ]
                    await viewmenu.stats_menu(
                        ctx=ctx,
                        data=data,
                        title=f"Top Openers For: {year}",
                        rows=10,
                    )
                else:
                    embed = await bot_embed.not_found_embed(
                        command="Stats",
                        message=f"Opener, Year: {year}",
                    )

                    await ctx.send(embed=embed)

    @closer.command(name="year", usage="<year>")
    async def closer_year_stats(
        self,
        ctx: commands.Context,
        *,
        year: str,
    ) -> None:
        """Get list of closers by year."""
        async with await db.create_pool() as pool:
            await ctx.typing()

            async with (
                pool.connection() as conn,
                conn.cursor(
                    row_factory=dict_row,
                ) as cur,
            ):
                res = await cur.execute(
                    """
                    SELECT
                        s1.song_name,
                        s.position,
                        count(*) AS total
                    FROM "setlists" s
                    LEFT JOIN "events" e USING (event_id)
                    LEFT JOIN "songs" s1 ON s1.id = s.song_id
                    WHERE s.position = 'Show Closer'
                        AND to_char(e.event_date, 'YYYY') = %s
                    GROUP BY s1.song_name, s.position
                    ORDER BY count(*) DESC
                    """,
                    (year,),
                )

                stats = await res.fetchall()

                if stats:
                    data = [
                        f"{index}. **{row['song_name']}** - *{row['total']} time(s)*"
                        for index, row in enumerate(stats)
                    ]
                    await viewmenu.stats_menu(
                        ctx=ctx,
                        data=data,
                        title=f"Top Closers For: {year}",
                        rows=10,
                    )
                else:
                    embed = await bot_embed.not_found_embed(
                        command="Stats",
                        message=f"Closer, Year: {year}",
                    )

                    await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """Load extension into bot."""
    await bot.add_cog(Stats(bot))
