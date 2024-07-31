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

            embed.set_image(
                url=file["cover_url"],
            )

            menu.add_page(embed=embed)

        await menu.start()

    @commands.command(name="cover", usage="<date>")
    async def get_covers(
        self,
        ctx: commands.Context,
        *,
        argument: str = "",
    ) -> list:
        """Get list of covers from my repo based on date."""
        if argument == "":
            await ctx.send_help(ctx.command)
            return

        async with await db.create_pool() as pool:
            await ctx.typing()

            async with pool.connection() as conn, conn.cursor(
                row_factory=dict_row,
            ) as cur:
                date = await utils.date_parsing(argument)

                try:
                    date.strftime("%Y-%m-%d")
                except AttributeError:
                    embed = await bot_embed.not_found_embed(
                        command=self.__class__.__name__,
                        message=argument,
                    )
                    await ctx.send(embed=embed)

                    return

                res = await cur.execute(
                    """SELECT cover_url FROM "covers" WHERE event_date=%(date)s""",
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

            embed.set_image(
                url=cover,
            )

            await ctx.send(embed=embed)

        elif len(files) > 1:
            await self.covers_embed(ctx, files, date)
        else:
            embed = await bot_embed.not_found_embed(
                command=self.__class__.__name__,
                message=argument,
            )
            await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """Load extension into bot."""
    await bot.add_cog(Cover(bot))
