import discord
import ftfy
import psycopg
from cogs.bot_stuff import bot_embed, db, utils, viewmenu
from discord.ext import commands
from psycopg.rows import dict_row


class Song(commands.Cog):
    """Collection of commands for getting info on different songs."""

    def __init__(self, bot: commands.Bot) -> None:
        """Init Song cog with bot."""
        self.bot = bot
        self.description = "Find songs that Bruce has played live."

    async def get_count_by_year(self, song_id: int, cur: psycopg.AsyncCursor) -> dict:
        """Use given id to count how many times a song has appeared by year."""
        res = await cur.execute(
            """
            SELECT
                to_char(e.event_date, 'YYYY') AS year,
                COUNT(s.song_id) AS count
            from setlists s
            LEFT JOIN events e ON e.event_id = s.event_id
            WHERE s.song_id = %(song)s
            AND s.set_name = ANY(ARRAY['Show', 'Set 1', 'Set 2', 'Encore', 'Pre-Show', 'Post-Show'])
            GROUP BY to_char(e.event_date, 'YYYY')
            ORDER BY to_char(e.event_date, 'YYYY')
            """,  # noqa: E501
            {"song": song_id},
        )

        return await res.fetchall()

    async def get_count_by_tour(self, song_id: int, cur: psycopg.AsyncCursor) -> dict:
        """Use given url to count how many times a song has appeared by year."""
        res = await cur.execute(
            """
            SELECT
                CASE
                    WHEN t.start_year = t.end_year THEN t.start_year::text
                    ELSE t.start_year || '-' || t.end_year
                END as years,
                t.tour_name AS tour,
                count(*)
            FROM setlists s
            LEFT JOIN events e ON e.event_id = s.event_id
            LEFT JOIN tours t ON t.id = e.tour_id
            WHERE
                s.song_id = %(song)s
                AND t.id <> ALL(ARRAY[43, 20, 23])
                AND s.set_name = ANY(ARRAY['Show', 'Set 1', 'Set 2', 'Encore', 'Pre-Show', 'Post-Show'])
            GROUP BY t.tour_name, t.start_year, t.end_year
            ORDER BY count(*) DESC
            """,  # noqa: E501
            {"song": song_id},
        )

        return await res.fetchall()

    async def get_song_info(self, song_id: int, cur: psycopg.AsyncCursor) -> dict:
        """With provided URL from fts, get info on song."""
        res = await cur.execute(
            """
            SELECT
                s.id,
                s.song_name,
                s.brucebase_url,
                e.event_id AS first_event,
                e.event_date AS first_date,
                e.brucebase_url AS first_url,
                e1.event_id AS last_event,
                e1.event_date AS last_date,
                e1.brucebase_url AS last_url,
                s.num_plays_public,
                round((s.num_plays_public /
                    (SELECT COUNT(event_id) FROM "events"
                    WHERE event_certainty=ANY(ARRAY['Confirmed', 'Probable']))::float * 100)::numeric, 2) AS frequency,
                coalesce(s1.num_post_release, 0) AS num_post_release,
                s.num_plays_private,
                s.num_plays_snippet,
                s.opener,
                s.closer,
                s.original_artist
            FROM "songs" s
            LEFT JOIN "events" e ON e.event_id = s.first_played
            LEFT JOIN "events" e1 ON e1.event_id = s.last_played
            LEFT JOIN "songs_after_release" s1 ON s1.song_id = s.id
            WHERE s.id = %(song_id)s
            """,  # noqa: E501
            {"song_id": song_id},
        )

        return await res.fetchone()

    async def get_first_release(
        self,
        song_id: int,
        cur: psycopg.AsyncCursor,
    ) -> dict:
        """Get info on the first release of a given song."""
        res = await cur.execute(
            """SELECT * FROM "songs_first_release"
                WHERE song_id=%s ORDER BY release_date::date ASC;""",
            (song_id,),
        )

        return await res.fetchone()

    async def calc_show_gap(
        self,
        cur: psycopg.AsyncCursor,
        last_show: str,
    ) -> int:
        """Get gap between shows."""
        res = await cur.execute(
            """
            SELECT
                MAX(event_num) - MIN(event_num) FILTER (WHERE event_id=%s) AS gap
            FROM "events"
            """,
            (last_show,),
        )

        show_gap = await res.fetchone()

        return show_gap["gap"]

    async def song_embed(
        self,
        song: dict,
        release: dict,
        ctx: commands.Context,
        cur: psycopg.AsyncCursor,
    ) -> discord.Embed:
        """Create the song embed and sending."""
        embed = await bot_embed.create_embed(
            ctx=ctx,
            title=song["song_name"],
        )

        try:
            embed.set_thumbnail(url=release["thumb"])
        except TypeError:
            embed.set_thumbnail(
                url="https://raw.githubusercontent.com/lilbud/brucebot/main/images/releases/default.jpg",
            )

        if release:
            embed.add_field(
                name="Original Release:",
                value=f"{release['name']} _({release['release_date']})_",
                inline=False,
            )

        if song["original_artist"] and song["original_artist"] != "Bruce Springsteen":
            embed.add_field(
                name="Original Artist:",
                value=song["original_artist"],
                inline=False,
            )

        embed.add_field(
            name="Performances:",
            value=f"{song['num_plays_public']} ({song['num_post_release']})",
        )

        if song["num_plays_public"] > 0:
            first_date_value = "None"
            last_date_value = "None"

            first_date_value = await utils.format_link(
                url=f"http://brucebase.wikidot.com{song['first_url']}",
                text=song["first_date"],
            )

            gap = await self.calc_show_gap(cur=cur, last_show=song["last_event"])

            last_date_value = await utils.format_link(
                url=f"http://brucebase.wikidot.com{song['last_url']}",
                text=f"{song['last_date']}",
            )

            embed.add_field(
                name="First Played:",
                value=first_date_value,
            )

            embed.add_field(
                name="Last Played:",
                value=f"{last_date_value} ({gap})",
            )

            embed.add_field(name="Opener:", value=song["opener"])
            embed.add_field(name="Closer:", value=song["closer"])
            embed.add_field(name="Frequency:", value=f"{song['frequency']}%")

            embed.add_field(
                name="Snippet:",
                value=f"{song['num_plays_snippet']}",
            )

        return embed

    @commands.hybrid_group(
        name="song",
        fallback="song",
        aliases=["s"],
        description="Get stats on a song",
        usage="<song>",
    )
    async def song_find(
        self,
        ctx: commands.Context,
        *,
        song: str,
    ) -> None:
        """Search database for song."""
        song = ftfy.fix_text(song)

        async with (
            await db.create_pool() as pool,
            pool.connection() as conn,
            conn.cursor(
                row_factory=dict_row,
            ) as cur,
        ):
            song_match = await utils.song_find_fuzzy(song, cur)

            if song_match:
                view = discord.ui.View()

                release = await self.get_first_release(
                    song_id=song_match["id"],
                    cur=cur,
                )

                song_info = await self.get_song_info(
                    song_id=song_match["id"],
                    cur=cur,
                )

                print(song_info)

                embed = await self.song_embed(
                    song=song_info,
                    release=release,
                    ctx=ctx,
                    cur=cur,
                )

                brucebase_button = discord.ui.Button(
                    style="link",
                    url=f"http://brucebase.wikidot.com{song_match['brucebase_url']}",
                    label="Brucebase",
                )

                view.add_item(item=brucebase_button)

                await ctx.send(embed=embed, view=view)

            else:
                embed = await bot_embed.not_found_embed(
                    command=self.__class__.__name__,
                    message=song,
                )
                await ctx.send(embed=embed)

    @song_find.command(
        name="tour",
        description="Get tour stats on a song",
        usage="<song>",
    )
    async def song_tour_count(
        self,
        ctx: commands.Context,
        *,
        song: str = "",
    ) -> None:
        """Search database by song and get tour counts."""
        if song == "":
            await ctx.send_help(ctx.command)
            return

        async with (
            await db.create_pool() as pool,
            pool.connection() as conn,
            conn.cursor(
                row_factory=dict_row,
            ) as cur,
        ):
            song_match = await utils.song_find_fuzzy(song, cur)

            if song_match:
                song_info = await self.get_song_info(
                    song_id=song_match["id"],
                    cur=cur,
                )

                tour_stats = await self.get_count_by_tour(
                    song_match["id"],
                    cur,
                )

                menu = await viewmenu.create_dynamic_menu(
                    ctx=ctx,
                    page_counter="Page $/&",
                    rows=12,
                    title=f"Tour Count For: {song_info['song_name']}",
                )

                for index, row in enumerate(tour_stats, start=1):
                    menu.add_row(
                        f"{index}. _{row['years']}_: **{row['tour']}** - _{row['count']} time(s)_",  # noqa: E501
                    )

                await menu.start()
            else:
                embed = await bot_embed.not_found_embed(
                    command=self.__class__.__name__,
                    message=song,
                )
                await ctx.send(embed=embed)

    @song_find.command(
        name="year",
        description="Get year stats on a song",
        usage="<song>",
    )
    async def song_year_count(
        self,
        ctx: commands.Context,
        *,
        song: str = "",
    ) -> None:
        """Search database by song and get year counts."""
        if song == "":
            await ctx.send_help(ctx.command)
            return

        async with (
            await db.create_pool() as pool,
            pool.connection() as conn,
            conn.cursor(
                row_factory=dict_row,
            ) as cur,
        ):
            song_match = await utils.song_find_fuzzy(song, cur)

            if song_match:
                song_info = await self.get_song_info(
                    song_id=song_match["id"],
                    cur=cur,
                )

                year_stats = await self.get_count_by_year(
                    song_match["id"],
                    cur,
                )

                menu = await viewmenu.create_dynamic_menu(
                    ctx=ctx,
                    page_counter="Page $/&",
                    rows=12,
                    title=f"Year Count For: {song_info['song_name']}",
                )

                for index, row in enumerate(year_stats, start=1):
                    menu.add_row(f"{index}. **{row['year']}**: _{row['count']}_")

                await menu.start()
            else:
                embed = await bot_embed.not_found_embed(
                    command=self.__class__.__name__,
                    message=song,
                )
                await ctx.send(embed=embed)

    async def snippet_song_count(self, song_id: int, cur: psycopg.AsyncCursor) -> dict:
        """Get count of songs that a snippet was included as part of."""
        res = await cur.execute(
            """
            SELECT
                distinct s1.song_name,
                s1.brucebase_url AS url,
                count(s1.id) AS count
            FROM snippets sn
            LEFT JOIN setlists s ON s.id = sn.setlist_song_id
            LEFT JOIN songs s1 ON s1.id = s.song_id
            WHERE sn.snippet_id = %(song_id)s
            GROUP BY s1.song_name, s1.brucebase_url
            ORDER BY count(s1.id) DESC
            """,
            {"song_id": song_id},
        )

        return await res.fetchall()

    @commands.hybrid_command(
        name="snippet",
        aliases=["snip"],
        description="Find stats on when a song was included in another",
        usage="<song>",
    )
    async def snippet_find(
        self,
        ctx: commands.Context,
        *,
        song: str,
    ) -> None:
        """Search database for songs as snippets."""
        song = ftfy.fix_text(song)

        async with (
            await db.create_pool() as pool,
            pool.connection() as conn,
            conn.cursor(
                row_factory=dict_row,
            ) as cur,
        ):
            song_match = await utils.song_find_fuzzy(song, cur)

            if song_match:
                res = await cur.execute(
                    """SELECT
                            count(sn.snippet_id) AS count,
                            MIN(e.event_date) AS first,
                            (SELECT brucebase_url FROM events WHERE
                                event_id = MIN(sn.event_id)) AS first_url,
                            MAX(e.event_date) AS last,
                            (SELECT brucebase_url FROM events WHERE
                                event_id = MAX(sn.event_id)) AS last_url
                        FROM snippets sn
                        LEFT JOIN events e ON e.event_id = sn.event_id
                        WHERE snippet_id = %s""",
                    (song_match["id"],),
                )

                snippet = await res.fetchone()

                snippet_songs = await self.snippet_song_count(
                    song_id=song_match["id"],
                    cur=cur,
                )

                release = await self.get_first_release(
                    song_id=song_match["id"],
                    cur=cur,
                )

                song_info = await self.get_song_info(
                    song_id=song_match["id"],
                    cur=cur,
                )

                embed = await bot_embed.create_embed(
                    ctx=ctx,
                    title=f"{song_info['song_name']} (snippet)",
                    url=f"http://brucebase.wikidot.com{song_info['brucebase_url']}",
                )

                if release:
                    embed.add_field(
                        name="Original Release:",
                        value=f"{release['name']} _({release['release_date']})_",
                        inline=False,
                    )

                try:
                    embed.set_thumbnail(url=release["thumb"])
                except TypeError:
                    embed.set_thumbnail(
                        url="https://raw.githubusercontent.com/lilbud/brucebot/main/images/releases/default.jpg",
                    )

                embed.add_field(name="Count:", value=snippet["count"])

                if snippet["count"] > 0:
                    embed.add_field(
                        name="First:",
                        value=f"[{snippet['first']}](<http://brucebase.wikidot.com{snippet['first_url']}>)",
                    )
                    embed.add_field(
                        name="Last:",
                        value=f"[{snippet['last']}](<http://brucebase.wikidot.com{snippet['last_url']}>)",
                    )

                if snippet_songs:
                    songs = [
                        f"[{song['song_name']}](http://brucebase.wikidot.com{song['url']}) - {song['count']} times(s)"  # noqa: E501
                        for song in snippet_songs
                    ]

                    embed.add_field(
                        name="Included During:",
                        value=f"{'\n'.join(songs)}",
                        inline=False,
                    )

                await ctx.send(embed=embed)
            else:
                embed = await bot_embed.not_found_embed(
                    command="snippet",
                    message=song,
                )
                await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """Load extension into bot."""
    await bot.add_cog(Song(bot))
