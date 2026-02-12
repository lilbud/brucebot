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
            title=album["name"],
        )

        try:
            embed.set_thumbnail(url=album["thumb"])
        except TypeError:
            embed.set_thumbnail(
                url="https://raw.githubusercontent.com/lilbud/brucebot/main/images/releases/default.jpg",
            )

        embed.add_field(name="Release Date:", value=album["release_date"], inline=True)
        embed.add_field(name="Album Type:", value=album["type"], inline=True)

        least = album_stats["least"]
        most = album_stats["most"]

        least_played_url = await utils.format_link(
            url=f"https://databruce.com/songs/{least['song_id']}",
            text=least["song_name"],
        )

        most_played_url = await utils.format_link(
            url=f"https://databruce.com/songs/{most['song_id']}",
            text=most["song_name"],
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
            WITH song_stats AS (
                SELECT
                    s.id AS song_id,
                    s.song_name,
                    COUNT(DISTINCT s1.*) FILTER (WHERE set_name IN ('Show', 'Set 1', 'Set 2', 'Encore')) AS times_played
                FROM "release_tracks" r
                LEFT JOIN "songs" s ON s.id = r.song_id
                LEFT JOIN "setlists" s1 ON s1.song_id = s.id
                WHERE r.release_id = %(id)s
                GROUP BY 1, 2
            ),
            ranked_stats AS (
                SELECT *,
                    RANK() OVER (ORDER BY times_played DESC) as most_played_rank,
                    RANK() OVER (ORDER BY times_played ASC) as least_played_rank
                FROM song_stats
            )
            SELECT 
                song_name,
                times_played,
                song_id,
                CASE WHEN most_played_rank = 1 THEN 'most' ELSE 'least' END as category
            FROM ranked_stats
            WHERE most_played_rank = 1 OR least_played_rank = 1
            ORDER BY times_played asc;
            """,
            {"id": album_id},
        )

        stats = await res.fetchall()

        return {"least": stats[0], "most": stats[-1]}

    async def album_search(self, query: str, cur: psycopg.AsyncCursor) -> dict:
        """Find album by query."""
        res = await cur.execute(
            """
            SELECT
                r.*,
                ts_rank_cd(fts_name_vector, websearch_to_tsquery('extensions.unaccent', %(query)s)) AS rank
            FROM
                releases r
            WHERE
                fts_name_vector @@ websearch_to_tsquery('extensions.unaccent', %(query)s)
            ORDER BY
                rank DESC
            LIMIT 1;
            """,  # noqa: E501
            {"query": ftfy.fix_text(query)},
        )

        return await res.fetchone()

    @commands.hybrid_command(
        name="album",
        aliases=["a"],
        usage="<album>",
        description="Search database for album.",
    )
    async def album_find(
        self,
        ctx: commands.Context,
        *,
        album: str,
    ) -> None:
        """Search database for album.

        Album can be found by name or short name
        """
        async with (
            await db.create_pool() as pool,
            pool.connection() as conn,
            conn.cursor(
                row_factory=dict_row,
            ) as cur,
        ):
            album = await self.album_search(album, cur)

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

                databruce_button = await utils.create_link_button(
                    url=f"https://www.databruce.com/releases/{album['id']}",
                    label="Databruce",
                )

                musicbrainz_button = await utils.create_link_button(
                    url=f"https://musicbrainz.org/release-group/{album['mbid']}",
                    label="MusicBrainz",
                )

                view.add_item(item=databruce_button)
                view.add_item(item=musicbrainz_button)

                await ctx.send(embed=embed, view=view)
            else:
                embed = await bot_embed.not_found_embed(
                    command=self.__class__.__name__,
                    message=album,
                )
                await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """Load extension into bot."""
    await bot.add_cog(Album(bot))
