from pathlib import Path

import discord
import psycopg
from cogs.bot_stuff import bot_embed, db, utils, viewmenu
from discord.ext import commands
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool


class Setlist(commands.Cog):
    """Collection of commands for pulling setlists for different shows."""

    def __init__(self, bot: commands.Bot) -> None:
        """Init Setlist cog with bot."""
        self.bot = bot
        self.imgpath = Path(Path(__file__).parents[2], "images", "releases")
        self.description = "Find setlists by date"

    async def get_latest_setlist(self, pool: AsyncConnectionPool) -> str:
        """When no date provided, get the most recent show."""
        async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            res = await cur.execute(
                """SELECT
                    MAX(e.event_date::text) AS date
                FROM "setlists" s
                LEFT JOIN "events" e USING(event_id)
                """,
            )

            latest = await res.fetchone()

            return latest["date"]

    async def get_event_notes(
        self,
        event_id: str,
        cur: psycopg.AsyncCursor,
    ) -> list[str]:
        """Get notes for an event and return."""
        res = await cur.execute(
            """
                SELECT DISTINCT
                    num::int,
                    '[' || num || '] ' || note AS formatted_note
                FROM
                    "setlist_notes"
                WHERE
                    event_id = %(event)s
                ORDER BY num::int
            """,
            {"event": event_id},
        )

        event_notes = await res.fetchall()

        print(event_notes)

        return [row["formatted_note"] for row in event_notes]

    async def get_events_by_exact_date(
        self,
        date: str,
        pool: AsyncConnectionPool,
    ) -> list["str"]:
        """Get events for a given date."""
        async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            res = await cur.execute(
                """
                    SELECT
                        e.*
                    FROM "events_with_info" e
                    WHERE e.event_date = %(date)s
                    AND e.event_date <= current_date
                    """,
                {"date": date},
            )

            return await res.fetchall()

    async def get_nugs_release(
        self,
        event_id: str,
        pool: AsyncConnectionPool,
    ) -> dict:
        """Get the cover of the nugs release if there is one."""
        async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            res = await cur.execute(
                """SELECT
                    nugs_url AS url
                FROM "nugs_releases"
                WHERE event_id=%s;""",
                (event_id,),
            )

            return await res.fetchone()

    async def get_archive_links(
        self,
        event_id: str,
        pool: AsyncConnectionPool,
    ) -> dict:
        """Get links to archive.org if i uploaded a tape."""
        async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            res = await cur.execute(
                """SELECT
                    archive_url AS url
                FROM "archive_links"
                WHERE event_id=%s;""",
                (event_id,),
            )

            return await res.fetchone()

    async def parse_brucebase_url(self, url: str, pool: AsyncConnectionPool) -> str:
        """Use provided Brucebase URL to pull the exact event instead of date."""
        async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            res = await cur.execute(
                """SELECT e.* FROM events_with_info e WHERE event_url=%s""",
                (url,),
            )

            return await res.fetchall()

    async def get_events_by_fuzzy_date(
        self,
        date: str,
        pool: AsyncConnectionPool,
    ) -> list[str]:
        """Get events for a given date."""
        async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            res = await cur.execute(
                """SELECT
                    e.*
                FROM
                    "events_with_info" e,
                    to_tsvector(event_date
                        || ' ' || to_char(event_date, 'FMMonth')
                        || ' ' || to_char(event_date, 'DD')
                        || ' ' || to_char(event_date, 'YY')
                        || ' ' || f_unaccent(venue_loc)
                        || ' ' || coalesce(state_name, '')
                        || ' ' || coalesce(formatted_date, '')
                        || ' ' || coalesce(event_title, '')) document,
                    plainto_tsquery(%(date)s) query
                WHERE query @@ document
                ORDER BY event_id ASC NULLS LAST
                LIMIT 16;""",
                {"date": date},
            )

            return await res.fetchall()

    async def setlist_embed(
        self,
        event: dict,
        ctx: commands.Context,
        pool: AsyncConnectionPool,
    ) -> discord.File | discord.Embed:
        """Create embed."""
        venue_url = await utils.format_link(event["venue_url"], event["venue_loc"])
        releases = []

        description = [f"**Venue:** {venue_url}"]

        if event["event_title"]:
            description.append(f"**Title:** {event['event_title']}")

        if event["note"]:
            description.append(f"**Notes:**\n- {event['note']}")

        nugs_release = await self.get_nugs_release(
            event_id=event["event_id"],
            pool=pool,
        )

        archive = await self.get_archive_links(event_id=event["event_id"], pool=pool)

        if nugs_release:
            releases.append(f"[Nugs]({nugs_release['url']})")

        if archive:
            releases.append(f"[Archive.org]({archive['url']})")

        if len(releases) > 0:
            description.append(f"**Releases:** {", ".join(releases)}")

        embed = await bot_embed.create_embed(
            ctx=ctx,
            title=event["formatted_date"],
            description="\n".join(description),
            url=event["event_url"],
        )

        async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            res = await cur.execute(
                """
                SELECT
                    s.set_name,
                    s.setlist
                FROM "setlists_by_set_and_date" s
                LEFT JOIN "events" e USING (event_id)
                WHERE s.event_id = %(event_id)s
                GROUP BY s.event_id, s.set_name, s.setlist, s.min
                ORDER BY s.min
                """,
                event,
            )

            setlist = await res.fetchall()

            notes = await self.get_event_notes(event_id=event["event_id"], cur=cur)

        if len(setlist) == 0:
            embed.add_field(
                name="Setlist:",
                value="_No Set Details Known_",
                inline=False,
            )
        else:
            for set_n in setlist:
                match event["setlist_certainty"]:
                    case "Incomplete":
                        set_name = (
                            f"{set_n["set_name"]} _(Setlist Possibly Incomplete)_:"
                        )
                    case _:
                        set_name = f"{set_n["set_name"]}:"

                embed.add_field(
                    name=set_name,
                    value=set_n["setlist"],
                    inline=False,
                )

        if len(notes) > 0:
            embed.add_field(name="", value="-" * 48, inline=False)

            embed.add_field(
                name="Setlist Notes:",
                value=f"```{"\n".join(notes)}```",
            )

        footer = f"{event['tour']}\nEvent: {event['event_certainty']} - Setlist: {event['setlist_certainty']}"  # noqa: E501
        embed.set_footer(text=footer)

        return embed

    @commands.command(name="setlist", aliases=["sl"], usage="<date>")
    async def get_setlists(
        self,
        ctx: commands.Context,
        *,
        argument: str = "",
    ) -> None:
        """Fetch setlists for a given date.

        Note: date must be past, not a future date.
        """
        async with await db.create_pool() as pool:
            await ctx.typing()

            if argument == "":
                argument = await self.get_latest_setlist(pool=pool)

            if "http://brucebase.wikidot.com" in argument:
                events = await self.parse_brucebase_url(argument, pool)
            else:
                date = await utils.date_parsing(argument)

                print(date)

                try:
                    date.strftime("%Y-%m-%d")
                except AttributeError:
                    embed = discord.Embed(
                        title="Incorrect Date Format",
                        description=f"Failed to parse given date: `{date}`",
                    )
                    await ctx.send(embed=embed)
                    return

                events = await self.get_events_by_exact_date(
                    date=date.strftime("%Y-%m-%d"),
                    pool=pool,
                )

            if events:
                if len(events) == 1:
                    event = events[0]
                    embed = await self.setlist_embed(event=event, ctx=ctx, pool=pool)

                    await ctx.send(embed=embed)
                elif len(events) > 1:
                    menu = await viewmenu.create_view_menu(
                        ctx=ctx,
                        style="Event $ of &",
                    )

                    embeds = [
                        await self.setlist_embed(event=event, ctx=ctx, pool=pool)
                        for event in events
                    ]

                    menu.add_pages(embeds)

                    await menu.start()
            else:
                embed = await bot_embed.not_found_embed(
                    command=self.__class__.__name__,
                    message=argument,
                )
                await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """Load extension into bot."""
    await bot.add_cog(Setlist(bot))
