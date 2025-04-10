from cogs.bot_stuff import bot_embed, db, utils, viewmenu
from discord.ext import commands
from psycopg.rows import dict_row


class Cover(commands.Cog):
    """Collection of commands for grabbing covers from my Github repo."""

    def __init__(self, bot: commands.Bot) -> None:
        """Init Cover cog with bot."""
        self.bot = bot
        self.description = "Fetch bootleg covers"

    async def covers_embed(
        self,
        ctx: commands.Context,
        files: list,
        date: str,
    ) -> None:
        """Embed for bootleg covers. Uses pages and viewmenu."""
        menu = await viewmenu.create_view_menu(ctx, title=f"Covers for: {date}")

        for file in files:
            embed = await bot_embed.create_embed(
                ctx,
                title=f"Covers for {date}",
            )

            embed.add_field(name="Source:", value=file["source"], inline=False)

            embed.set_image(
                url=file["cover_url"],
            )

            menu.add_page(embed=embed)

        await menu.start()

    @commands.hybrid_command(
        name="cover",
        description="Get list of covers from my repo based on date.",
        usage="<date>",
    )
    async def get_covers(
        self,
        ctx: commands.Context,
        *,
        date: str,
    ) -> list:
        """Get list of covers from my repo based on date."""
        async with (
            await db.create_pool() as pool,
            pool.connection() as conn,
            conn.cursor(
                row_factory=dict_row,
            ) as cur,
        ):
            date = await utils.date_parsing(date)

            try:
                date.strftime("%Y-%m-%d")
            except AttributeError:
                embed = await bot_embed.not_found_embed(
                    command=self.__class__.__name__,
                    message=date,
                )
                await ctx.send(embed=embed)

                return

            res = await cur.execute(
                """SELECT cover_url, 'lilbud' AS source FROM "covers"
                    WHERE event_date=%(date)s""",
                {"date": date.strftime("%Y-%m-%d")},
            )

            files = await res.fetchall()

            if len(files) == 0:
                res = await cur.execute(
                    """SELECT
                            n.thumbnail_url AS cover_url,
                            'Nugs' AS source
                        FROM nugs_releases n
                        LEFT JOIN events e ON e.event_id = n.event_id
                        WHERE e.event_date = %(date)s""",
                    {"date": date.strftime("%Y-%m-%d")},
                )

                files = await res.fetchall()

        # ViewMenu is only for multiple covers,
        # single embed is just default embed + image.
        if len(files) == 1:
            cover = files[0]["cover_url"]
            embed = await bot_embed.create_embed(
                ctx,
                title=f"Cover for {date}",
            )

            embed.add_field(name="Source:", value=files[0]["source"], inline=False)

            embed.set_image(
                url=cover,
            )

            await ctx.send(embed=embed)

        elif len(files) > 1:
            await self.covers_embed(ctx, files, date)
        else:
            embed = await bot_embed.not_found_embed(
                command=self.__class__.__name__,
                message=date,
            )
            await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """Load extension into bot."""
    await bot.add_cog(Cover(bot))
