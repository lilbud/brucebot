from cogs.bot_stuff import bot_embed, db, viewmenu
from discord.ext import commands
from psycopg.rows import dict_row


class User(commands.Cog):
    """Collection of commands for getting user info."""

    def __init__(self, bot: commands.Bot) -> None:
        """Init Song cog with bot."""
        self.bot = bot
        self.description = "Find songs that Bruce has played live."

    @commands.hybrid_command(
        name="user_stats",
        aliases=["us", "user", "userstats"],
        usage="<username>",
        description="Get stats for a given user.",
    )
    async def user_stats(self, ctx: commands.Context, *, username: str = "") -> None:
        """Get stats for a given user."""
        async with (
            await db.create_pool() as pool,
            pool.connection() as conn,
            conn.cursor(
                row_factory=dict_row,
            ) as cur,
        ):
            if username == "":
                username = ctx.author.name

            res = await cur.execute(
                """
                select
                    distinct au.id,
                    au.uuid as user_id,
                    min(e.event_id) as first_id,
                    min(e.event_date) as first_date,
                    max(e.event_id) as last_id,
                    max(e.event_date) as last_date,
                    count(distinct e.event_id) as event_count,
                    count(distinct s.song_id) filter (where s.set_name in ('Show', 'Set 1', 'Set 2', 'Encore', 'Pre-Show')) as song_count
                from
                auth_user au
                left join user_attended_shows u on u.user_id = au.id
                left join events e on e.id = u.event_id
                left join setlists s on s.event_id = e.id
                where
                    lower(discord_name) = %(username)s
                group by 1
                """,
                {"username": username.lower()},
            )

            stats = await res.fetchone()

            if stats:
                embed = await bot_embed.create_embed(
                    ctx,
                    f"{username} Stats",
                    "",
                    f"https://www.databruce.com/profile/{stats['user_id']}",
                )

                # embed.set_thumbnail(url=ctx.author.avatar.url)

                embed.add_field(
                    name="First Event:",
                    value=f"[{stats['first_date']}](https://www.databruce.com/events/{stats['first_id']})",
                    inline=False,
                )

                embed.add_field(
                    name="Last Event:",
                    value=f"[{stats['last_date']}](https://www.databruce.com/events/{stats['last_id']})",
                    inline=False,
                )

                embed.add_field(
                    name="Events Attended:",
                    value=stats["event_count"],
                    inline=False,
                )

                embed.add_field(
                    name="Songs Played:",
                    value=stats["song_count"],
                    inline=False,
                )

                await ctx.send(embed=embed)
            else:
                embed = await bot_embed.not_found_embed(
                    command=self.__class__.__name__,
                    message=username,
                )
                await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="users",
        usage="<username>",
        description="Get stats for a given user.",
    )
    async def users(self, ctx: commands.Context, *, discord: str = "") -> None:
        """Get all Databruce users who have seen a show"""
        async with (
            await db.create_pool() as pool,
            pool.connection() as conn,
            conn.cursor(
                row_factory=dict_row,
            ) as cur,
        ):
            menu = await viewmenu.create_dynamic_menu(
                ctx=ctx,
                page_counter="Page $/&\tData from Databruce",
                rows=10,
                title="User Leaderboard",
            )

            if discord.lower() == "discord":
                menu = await viewmenu.create_dynamic_menu(
                    ctx=ctx,
                    page_counter="Page $/&\nData from Databruce",
                    rows=10,
                    title="User Leaderboard\n(Discord Users Only)",
                )

                res = await cur.execute(
                    """
                    select
                        au.username,
                        au.uuid,
                        count(distinct e.event_id) as event_count
                    from
                        auth_user au
                        left join user_attended_shows u on u.user_id = au.id
                        left join events e on e.id = u.event_id
                        left join setlists s on s.event_id = e.id
                    where e.event_id is not null and au.discord_name is not null
                    group by au.id
                    order by 3 desc
                    """,
                )
            else:
                res = await cur.execute(
                    """
                    select
                        au.username,
                        au.uuid,
                        count(distinct e.event_id) as event_count
                    from
                        auth_user au
                        left join user_attended_shows u on u.user_id = au.id
                        left join events e on e.id = u.event_id
                        left join setlists s on s.event_id = e.id
                    where e.event_id is not null
                    group by au.id
                    order by 3 desc
                    """,
                )

            users = await res.fetchall()

            for index, user in enumerate(users, start=1):
                event_count = user["event_count"]
                menu.add_row(
                    f"**{index}.** [{user['username']}](https://www.databruce.com/profile/{user['uuid']}) - {event_count} shows",
                )

            await menu.start()


async def setup(bot: commands.Bot) -> None:
    """Load extension into bot."""
    await bot.add_cog(User(bot))
