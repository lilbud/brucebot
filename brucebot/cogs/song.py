import discord
import psycopg
from cogs.bot_stuff import bot_embed, db, utils
from discord.ext import commands
from psycopg.rows import dict_row


class Song(commands.Cog):
    """Collection of commands for getting info on different songs."""

    def __init__(self, bot: commands.Bot) -> None:
        """Init Song cog with bot."""
        self.bot = bot
        self.description = "Find songs that Bruce has played live."

    async def get_song_info(self, url: str, cur: psycopg.AsyncCursor) -> dict:
        """With provided URL from fts, get info on song."""
        res = await cur.execute(
            """
            SELECT
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
                    (SELECT COUNT(event_id) FROM "event_details"
                    WHERE event_certainty=ANY(ARRAY['Confirmed', 'Probable']))::float * 100)::numeric, 2) AS frequency,
                coalesce(s1.num_post_release, 0) AS num_post_release,
                s.opener,
                s.closer,
                s.original_artist
            FROM "songs" s
            LEFT JOIN "events" e ON e.event_id = s.first_played
            LEFT JOIN "events" e1 ON e1.event_id = s.last_played
            LEFT JOIN "songs_after_release" s1 ON s1.song_id = s.brucebase_url
            WHERE s.brucebase_url = %(url)s
            """,  # noqa: E501
            {"url": url},
        )

        return await res.fetchone()

    async def get_first_release(
        self,
        song: str,
        cur: psycopg.AsyncCursor,
    ) -> dict:
        """Get info on the first release of a given song."""
        res = await cur.execute(
            """SELECT * FROM "songs_first_release"
                WHERE song_id=%s ORDER BY date::date ASC;""",
            (song,),
        )

        return await res.fetchone()

    async def calc_show_gap(
        self,
        cur: psycopg.AsyncCursor,
        last_show: str,
    ) -> int:
        """Get gap between shows."""
        res = await cur.execute(
            """SELECT event_num::int AS num FROM "events" WHERE event_id=%s""",
            (last_show,),
        )

        last_show_num = await res.fetchone()

        res = await cur.execute(
            """SELECT event_num::int AS num FROM "events" WHERE
                event_id=(SELECT MAX(event_id) FROM "setlists")""",
        )

        most_recent_show_num = await res.fetchone()

        return most_recent_show_num["num"] - last_show_num["num"]

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
            embed.set_thumbnail(url=release["release_thumb"])
        except TypeError:
            embed.set_thumbnail(
                url="https://raw.githubusercontent.com/lilbud/brucebot/main/images/releases/default.jpg",
            )

        if release:
            embed.add_field(
                name="Original Release:",
                value=f"{release['release_name']} ({release['date']})",
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
            value=f"{song["num_plays_public"]} ({song["num_post_release"]})",
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
                text=f"{song["last_date"]}",
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
            embed.add_field(name="Frequency:", value=f"{song["frequency"]}%")

        return embed

    async def song_find_fuzzy(
        self,
        query: str,
        cur: psycopg.AsyncCursor,
    ) -> dict:
        """Fuzzy search SONGS table using full text search."""
        res = await cur.execute(
            """
            SELECT
                s.brucebase_url,
                rank,
                similarity
            FROM
                "songs" s,
                plainto_tsquery('english', %(query)s) query,
                ts_rank(fts, query) rank,
                SIMILARITY(%(query)s, coalesce(aliases, short_name, song_name)) similarity
            WHERE query @@ fts AND similarity >= 0.45
            ORDER BY similarity DESC, rank DESC;
            """,  # noqa: E501
            {"query": query},
        )

        return await res.fetchone()

    @commands.command(name="song", aliases=["s"], usage="<song>")
    async def song_find(
        self,
        ctx: commands.Context,
        *,
        argument: str = "",
    ) -> None:
        """Search database for song."""
        if argument == "":
            await ctx.send_help(ctx.command)
            return

        argument = await utils.clean_message(argument)

        async with await db.create_pool() as pool:
            await ctx.typing()

            async with pool.connection() as conn, conn.cursor(
                row_factory=dict_row,
            ) as cur:
                song = await self.song_find_fuzzy(argument, cur)

                if song:
                    view = discord.ui.View()

                    release = await self.get_first_release(
                        song=song["brucebase_url"],
                        cur=cur,
                    )

                    song_info = await self.get_song_info(
                        url=song["brucebase_url"],
                        cur=cur,
                    )

                    embed = await self.song_embed(
                        song=song_info,
                        release=release,
                        ctx=ctx,
                        cur=cur,
                    )

                    brucebase_button = discord.ui.Button(
                        style="link",
                        url=f"http://brucebase.wikidot.com/song:{song['brucebase_url']}",
                        label="Brucebase",
                    )

                    view.add_item(item=brucebase_button)

                    await ctx.send(embed=embed, view=view)

                else:
                    embed = await bot_embed.not_found_embed(
                        command=self.__class__.__name__,
                        message=argument,
                    )
                    await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """Load extension into bot."""
    await bot.add_cog(Song(bot))
