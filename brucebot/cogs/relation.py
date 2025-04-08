import discord
import psycopg
from cogs.bot_stuff import bot_embed, db
from discord.ext import commands
from psycopg.rows import dict_row


class Relation(commands.Cog):
    """Collection of commands for searching various people with a Bruce history."""

    def __init__(self, bot: commands.Bot) -> None:
        """Init Relation cog with bot."""
        self.bot = bot
        self.description = "Find people with a Bruce history"

    async def not_found_embed(
        self,
        ctx: commands.Context,
        relation_name: str,
    ) -> None:
        """Embed if no relations found for the given date."""
        embed = await bot_embed.create_embed(
            ctx=ctx,
            title="No Relations Found",
            description=f"No people found for query: `{relation_name}`",
        )

        await ctx.send(embed=embed)

    async def get_relation_info(
        self,
        relation_id: int,
        cur: psycopg.AsyncCursor,
    ) -> dict:
        """Get info for relation by id."""
        res = await cur.execute(
            """SELECT
                r.brucebase_url,
                r.relation_name,
                r.appearances,
                r.aliases,
                e.event_date AS first_date,
                e.brucebase_url AS first_url,
                e1.event_date AS last_date,
                e1.brucebase_url AS last_url
            FROM "relations" r
            LEFT JOIN "events" e ON e.event_id = r.first_appearance
            LEFT JOIN "events" e1 ON e1.event_id = r.last_appearance
            WHERE r.id = %s""",
            (relation_id,),
        )

        return await res.fetchone()

    async def relation_embed(
        self,
        relation: dict,
        ctx: commands.Context,
    ) -> discord.Embed:
        """Create the song embed and sending."""
        embed = await bot_embed.create_embed(
            ctx=ctx,
            title=relation["relation_name"],
            description=f"**Nicknames:** {relation['aliases']}",
            url=f"http://brucebase.wikidot.com/relation:{relation['brucebase_url']}",
        )

        embed.add_field(name="Appearances", value=relation["appearances"])

        embed.add_field(
            name="First Appearance:",
            value=f"[{relation['first_date']}](http://brucebase.wikidot.com{relation['first_url']})",
        )

        embed.add_field(
            name="Last Appearance:",
            value=f"[{relation['last_date']}](http://brucebase.wikidot.com{relation['last_url']})",
        )

        return embed

    # name, num_appearances, first, last
    @commands.hybrid_command(name="relation", aliases=["rel"], usage="<person>")
    async def relation_find(
        self,
        ctx: commands.Context,
        *,
        relation_query: str,
    ) -> None:
        """Find relation based on input.

        Can search by name or nickname (Big Man, Phantom, etc.)
        """
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
                        id,
                        rank,
                        similarity
                    FROM
                        "relations",
                        plainto_tsquery('english', %(query)s) query,
                        ts_rank(fts, query) rank,
                        SIMILARITY(%(query)s,
                            unaccent(relation_name) || ' ' ||
                            coalesce(aliases, '')) similarity
                    WHERE query @@ fts
                    ORDER BY appearances DESC, rank DESC, similarity DESC NULLS LAST LIMIT 1
                    """,  # noqa: E501
                    {"query": relation_query},
                )

                relation = await res.fetchone()

                if relation is not None:
                    relation_info = await self.get_relation_info(
                        relation_id=relation["id"],
                        cur=cur,
                    )

                    embed = await self.relation_embed(relation=relation_info, ctx=ctx)

                    await ctx.send(embed=embed)
                else:
                    embed = await bot_embed.not_found_embed(
                        command=self.__class__.__name__,
                        message=relation_query,
                    )
                    await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """Load extension into bot."""
    await bot.add_cog(Relation(bot))
