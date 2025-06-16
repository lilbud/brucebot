import re

import psycopg
from cogs.bot_stuff import bot_embed, db, viewmenu
from discord.ext import commands
from psycopg.rows import dict_row


class EveryTimePlayed(commands.Cog):
    """ETP Test."""

    def __init__(self, bot: commands.Bot) -> None:
        """Init cog with bot."""
        self.bot = bot
        self.description = ""

    async def song_find_fuzzy(
        self,
        query: str,
        cur: psycopg.AsyncCursor,
    ) -> dict:
        """Fuzzy search SONGS table using full text search."""
        res = await cur.execute(
            """
            SELECT
                s.song_name,
                rank,
                similarity
            FROM
                "songs" s,
                plainto_tsquery('english', %(query)s) query,
                ts_rank(fts, query) rank,
                similarity(%(query)s, coalesce(short_name, song_name)) similarity
            WHERE query @@ fts
            ORDER BY similarity DESC, rank DESC;
            """,
            {"query": query},
        )

        song = await res.fetchone()
        return song["song_name"]

    async def etp_follow(
        self,
        song1: str,
        song2: str,
        cur: psycopg.AsyncCursor,
    ) -> list[dict]:
        """Test."""
        res = await cur.execute(
            """SELECT * FROM every_time_played
                WHERE song_name SIMILAR TO %(s1)s AND next SIMILAR TO %(s2)s
                ORDER BY event_date""",
            {"s1": f"{re.escape(song1)}_*", "s2": f"{re.escape(song2)}_*"},
        )

        return await res.fetchall()

    @commands.command(name="etp", usage="<song1> [follow] <song2>")
    async def etp_find(self, ctx: commands.Context, *, argument: str = "") -> None:
        """Text."""
        if argument == "":
            await ctx.send_help(ctx.command)
            return

        await ctx.typing()

        async with await db.create_pool() as pool:  # noqa: SIM117
            async with (
                pool.connection() as conn,
                conn.cursor(
                    row_factory=dict_row,
                ) as cur,
            ):
                # both songs present/song anywhere
                if ">" in argument:
                    arg_split = [song.strip() for song in argument.split(">")][0:2]
                    song1 = await self.song_find_fuzzy(arg_split[0], cur)
                    song2 = await self.song_find_fuzzy(arg_split[1], cur)
                    title = f"Times that {song1} was followed by {song2}"

                    etp_result = await self.etp_follow(song1, song2, cur)

                    print(etp_result)

                    if len(etp_result) > 0:
                        menu = await viewmenu.create_dynamic_menu(
                            ctx,
                            "Page $/&",
                            rows=10,
                            title=title,
                        )

                        for index, result in enumerate(etp_result):
                            row = f"{index}. **{result['event_date']} [{result['day']}]** - _{result['venue_loc']}_"  # noqa: E501
                            menu.add_row(data=row)

                        await menu.start()
                    else:
                        embed = await bot_embed.not_found_embed(
                            command=self.__class__.__name__,
                            message=argument,
                        )
                        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """Load extension into bot."""
    await bot.add_cog(EveryTimePlayed(bot))
