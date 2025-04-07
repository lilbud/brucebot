import discord
import ftfy
import psycopg
from cogs.bot_stuff import bot_embed, db, utils
from discord.ext import commands
from psycopg.rows import dict_row


class Album(commands.Cog):
    """Collection of commands for searching albums."""

    def __init__(self, bot: commands.Bot) -> None:
        """Init Album cog with bot."""
        self.bot = bot
        self.description = "Find Bruce's albums"

    async def album_embed(
        self,
        album: dict,
        album_stats: dict,
        ctx: commands.Context,
    ) -> discord.Embed:
        """Create embed with provided album info and send."""
        embed = await bot_embed.create_embed(
            ctx=ctx,
            title=album["release_name"],
        )

        if album["release_thumb"]:
            embed.set_thumbnail(url=album["release_thumb"])
        else:
            embed.set_thumbnail(
                url="https://raw.githubusercontent.com/lilbud/brucebot/main/images/releases/default.jpg",
            )

        embed.add_field(name="Release Date:", value=album["release_date"], inline=True)
        embed.add_field(name="Album Type:", value=album["release_type"], inline=True)

        least_played_url = await utils.format_link(
            url=album_stats["least"]["url"],
            text=album_stats["least"]["song_name"],
        )

        most_played_url = await utils.format_link(
            url=album_stats["most"]["url"],
            text=album_stats["most"]["song_name"],
        )

        embed.add_field(
            name="Least Played",
            value=f"{least_played_url} ({album_stats['least']['times_played']})",
            inline=False,
        )

        embed.add_field(
            name="Most Played",
            value=f"{most_played_url} ({album_stats['most']['times_played']})",
            inline=True,
        )

        return embed

    async def get_album_stats(
        self,
        album_id: int,
        cur: psycopg.AsyncCursor,
    ) -> dict[dict, dict]:
        """Get album tracks for the provided ID."""
        res = await cur.execute(
            """
            SELECT
                r.release_id,
                'http://brucebase.wikidot.com/song:' || s.brucebase_url AS url,
                s.song_name,
                s.num_plays_public AS times_played
            FROM "release_tracks" r
            LEFT JOIN "songs" s ON s.id = r.song_id
            WHERE r.release_id = %(id)s
            ORDER BY s.num_plays_public ASC
            """,
            {"id": album_id},
        )

        stats = await res.fetchall()

        return {"least": stats[0], "most": stats[-1]}

    @staticmethod
    async def album_search(query: str, cur: psycopg.AsyncCursor) -> dict:
        """Find album by query."""
        res = await cur.execute(
            """
            SELECT
                r.id,
                r.brucebase_id,
                r.mbid,
                r.name AS release_name,
                r.type AS release_type,
                to_char(r.release_date, 'FMMonth DD, YYYY') AS release_date,
                r.thumb AS release_thumb
            FROM
                "releases" r,
                plainto_tsquery('english', %(query)s) query,
                ts_rank(fts, query) rank,
                SIMILARITY(%(query)s, coalesce(short_name, name)) similarity
            WHERE query @@ fts
            ORDER BY similarity DESC, rank DESC;
            """,
            {"query": ftfy.fix_text(query)},
        )

        return await res.fetchone()

    @commands.command(
        name="album",
        aliases=["a"],
        usage="<album>",
        brief="Search database for album.",
    )
    async def album_find(
        self,
        ctx: commands.Context,
        *,
        album_query: str,
    ) -> None:
        """Search database for album.

        Album can be found by name or alias.
        """
        async with await db.create_pool() as pool:
            await ctx.typing()

            async with (
                pool.connection() as conn,
                conn.cursor(
                    row_factory=dict_row,
                ) as cur,
            ):
                album = await self.album_search(album_query, cur)

                if album:
                    view = discord.ui.View()

                    stats = await self.get_album_stats(
                        album_id=album["id"],
                        cur=cur,
                    )

                    embed = await self.album_embed(
                        album=album,
                        album_stats=stats,
                        ctx=ctx,
                    )

                    brucebase_button = await utils.create_link_button(
                        url=f"http://brucebase.wikidot.com{album['brucebase_id']}",
                    )
                    musicbrainz_button = await utils.create_link_button(
                        url=f"https://musicbrainz.org/release/{album['mbid']}",
                    )

                    view.add_item(item=brucebase_button)
                    view.add_item(item=musicbrainz_button)

                    await ctx.send(embed=embed, view=view)
                else:
                    embed = await bot_embed.not_found_embed(
                        command=self.__class__.__name__,
                        message=album_query,
                    )
                    await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """Load extension into bot."""
    await bot.add_cog(Album(bot))
