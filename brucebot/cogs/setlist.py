import datetime
import re
from pathlib import Path

import discord
import psycopg
import reactionmenu
import reactionmenu.errors
from cogs.bot_stuff import bot_embed, db, utils, viewmenu
from dateutil.parser import ParserError
from discord.ext import commands
from psycopg.rows import dict_row


class Setlist(commands.Cog):
    """Collection of commands for pulling setlists for different shows."""

    def __init__(self, bot: commands.Bot) -> None:
        """Init Setlist cog with bot."""
        self.bot = bot
        self.imgpath = Path(Path(__file__).parents[2], "images", "releases")
        self.description = "Find setlists by date"

    async def get_latest_setlist(self, cur: psycopg.AsyncCursor) -> str:
        """When no date provided, get the most recent show."""
        res = await cur.execute(
            """SELECT
                MAX(e.event_id) AS id
            FROM "setlists" s
            LEFT JOIN "events" e on e.id = s.event_id
            """,
        )

        return await res.fetchone()

    async def get_event_notes(
        self,
        event_id: str,
        cur: psycopg.AsyncCursor,
    ) -> list[str]:
        """Get notes for an event and return."""
        res = await cur.execute(
            """
            SELECT
                s.num,
                s.note
            FROM
            setlist_notes_new s
            LEFT JOIN events e ON e.event_id = s.event_id
            WHERE e.event_id = %(event)s
            ORDER BY num
            """,
            {"event": event_id},
        )

        return [f"\t\t[{row['num']}] {row['note']}" for row in await res.fetchall()]

    async def get_run(
        self,
        event: str,
        cur: psycopg.AsyncCursor,
    ) -> str:
        """Get the position and number of shows in a run for a run and event."""
        res = await cur.execute(
            """
            SELECT run_name FROM (
                SELECT
                    e.event_id,
                    r.name || ' (' ||
                        row_number() OVER (PARTITION BY e.run ORDER BY e.event_id) || '/' ||
                        count(e.event_id) OVER (PARTITION BY e.run) || ')' AS run_name
                FROM events e
                LEFT JOIN runs r ON r.id = e.run
            ) t WHERE t.event_id = %(event)s
            """,  # noqa: E501
            {"event": event},
        )

        run = await res.fetchone()
        return run["run_name"]

    async def get_events_by_exact_date(
        self,
        date: str,
        cur: psycopg.AsyncCursor,
    ) -> list["str"]:
        """Get events for a given date."""
        res = await cur.execute(
            """
                SELECT DISTINCT
                    e.*,
                    v.id as venue_id,
                    v.full_location AS venue_loc,
                    t1.name AS tour_leg,
                    r.name AS run,
                    t.tour_name AS tour
                FROM "events" e
                LEFT JOIN tours t ON t.id = e.tour_id
                LEFT JOIN venues_text v ON v.id = e.venue_id
                LEFT JOIN venues v1 ON v1.id = e.venue_id
                LEFT JOIN tour_legs t1 ON t1.id = e.tour_leg
                LEFT JOIN runs r ON r.id = e.run
                WHERE e.event_date = %(date)s
                ORDER BY e.event_id
                """,
            {"date": date},
        )

        return await res.fetchall()

    async def get_event_by_id(
        self,
        event: str,
        cur: psycopg.AsyncCursor,
    ) -> list["str"]:
        """Get event for a given id.

        Used when the input is the Databruce ID (YYYYMMDD-XX).
        """
        res = await cur.execute(
            """
                SELECT DISTINCT
                    e.*,
                    v.id as venue_id,
                    v.full_location AS venue_loc,
                    t1.name AS tour_leg,
                    r.name AS run,
                    t.tour_name AS tour
                FROM "events" e
                LEFT JOIN tours t ON t.id = e.tour_id
                LEFT JOIN venues_text v ON v.id = e.venue_id
                LEFT JOIN venues v1 ON v1.id = e.venue_id
                LEFT JOIN tour_legs t1 ON t1.id = e.tour_leg
                LEFT JOIN runs r ON r.id = e.run
                WHERE e.event_id = %(event)s
                ORDER BY e.event_id
                """,
            {"event": event},
        )

        return await res.fetchall()

    async def get_releases(
        self,
        event_id: str,
        cur: psycopg.AsyncCursor,
    ) -> list:
        """Get all releases, nugs and/or archive if exist."""
        res = await cur.execute(
            """
            SELECT unnest(array_remove(array[nugs, archive, release], NULL)) AS links FROM (
                SELECT
                    '[' || n.name || '](' || n.nugs_url || ')' AS nugs,
                    '[Archive.org](https://archive.org/details/' || a.archive_url || ')' AS archive,
                    coalesce(r.name, null) AS release
                FROM events e
                LEFT JOIN archive_links a on a.event_id = e.id
                LEFT JOIN "nugs_releases" n on n.event_id = e.id
                LEFT JOIN releases r on r.event_id = e.id
                WHERE e.event_id=%(event)s
            ) t
            """,
            {"event": event_id},
        )

        return [rel["links"] for rel in await res.fetchall()]

    async def parse_brucebase_url(self, url: str, cur: psycopg.AsyncCursor) -> str:
        """Use provided Brucebase URL to get event_id."""
        url = re.sub(r"(http\:\/\/)?brucebase.wikidot.com", "", url)

        res = await cur.execute(
            """SELECT e.event_id AS id FROM events e WHERE brucebase_url=%(url)s""",
            {"url": url},
        )

        return await res.fetchone()

    async def setlist_embed(
        self,
        event: dict,
        ctx: commands.Context,
        cur: psycopg.AsyncCursor,
    ) -> discord.File | discord.Embed:
        """Create embed."""
        # venue_url = await utils.format_link(event["venue_url"], event["venue_loc"])

        description = [
            f"**Venue:** [{event['venue_loc']}](https://www.databruce.com/venues/{event['venue_id']})",
        ]

        if event["event_title"]:
            description.append(f"**Title:** {event['event_title']}")

        if event["tour"]:
            text = f"**Tour:** {event['tour']}"

            if event["tour_leg"]:
                text = f"**Tour/Leg:** {event['tour']} / {event['tour_leg']}"

            description.append(text)

        if event["note"]:
            notes = []
            for i in str(event["note"]).splitlines():
                if "<br>" not in i:
                    i = re.sub(r"\[(.*)\]\(.*\)", r"\1", i)

                    notes.append(f"- {i}")

            if notes:
                description.append(f"**Notes:**\n{'\n'.join(notes)}")

        releases = await self.get_releases(event["event_id"], cur)

        if len(releases) > 0:
            description.append(f"**Releases:** {', '.join(releases)}")

        title = f"{event['event_date'].strftime('%Y-%m-%d [%a]')}"

        if event["early_late"]:
            title = (
                f"{event['event_date'].strftime('%Y-%m-%d [%a]')} {event['early_late']}"
            )

        embed = await bot_embed.create_embed(
            ctx=ctx,
            title=title,
            description="\n".join(description),
            url=f"https://www.databruce.com/events/{event['event_id']}",
        )

        res = await cur.execute(
            """
            SELECT
                s.set_name,
                s.setlist
            FROM "setlists_by_set_and_date" s
            LEFT JOIN "events" e on e.event_id = s.event_id
            WHERE e.event_id = %(event_id)s
            GROUP BY s.set_order, s.set_name, s.setlist
            order by s.set_order
            """,
            event,
        )

        setlist = await res.fetchall()

        notes = await self.get_event_notes(event_id=event["event_id"], cur=cur)

        if len(setlist) == 0:
            if (
                event["event_date"]
                > datetime.datetime.now(tz=datetime.timezone.utc).date()
            ):
                embed.add_field(
                    name="Setlist:",
                    value="_Event Hasn't Happened Yet_",
                    inline=False,
                )
            else:
                embed.add_field(
                    name="Setlist:",
                    value="_No Set Details Known_",
                    inline=False,
                )
        else:
            for set_n in setlist:
                match event["setlist_certainty"]:
                    case "Incomplete":
                        set_name = f"{set_n['set_name']} _(Incomplete)_:"
                    case _:
                        set_name = f"{set_n['set_name']}:"

                embed.add_field(
                    name=set_name,
                    value=set_n["setlist"],
                    inline=False,
                )

        if len(notes) > 0:
            embed.add_field(
                name="Setlist Notes:",
                value=f"{re.sub("''", "'", '\n'.join(notes))}",
            )

        event_info = {
            "run": await self.get_run(event["event_id"], cur),
            "event": event["event_certainty"],
            "setlist": event["setlist_certainty"],
        }

        footer = "\n".join(
            [
                f"{key.title()}: {value}"
                for key, value in event_info.items()
                if value is not None
            ],
        )
        embed.set_footer(text=f"\n{footer}")

        return embed

    @commands.command(name="latest", aliases=["last"])
    async def get_latest(
        self,
        ctx: commands.Context,
        cur: psycopg.AsyncCursor,
    ) -> None:
        """Get most recent show."""
        date = await self.get_latest_setlist(cur)

        await ctx.invoke(self.bot.get_command("setlist"), date=date)

    @commands.hybrid_command(
        name="setlist",
        aliases=["sl"],
        description="Fetch setlists for a given date, leave empty to get most recent.",
        usage="<date>",
    )
    async def get_setlists(
        self,
        ctx: commands.Context,
        *,
        date: str = "",
    ) -> None:
        """Fetch setlists for a given date.

        Note: date must be past, not a future date.
        """
        async with (
            await db.create_pool() as pool,
            pool.connection() as conn,
            conn.cursor(
                row_factory=dict_row,
            ) as cur,
        ):
            if re.search(r"\/(gig|rehearsal|nogig|recording|nobruce):", date):
                event = await self.parse_brucebase_url(date, cur)
                events = await self.get_event_by_id(event["id"], cur)

            elif date == "":
                event = await self.get_latest_setlist(cur)
                events = await self.get_event_by_id(event["id"], cur)

            elif re.search(r"\d{8}-\d{2}", date):  # databruce_id
                events = await self.get_event_by_id(date, cur)

            else:
                date = await utils.date_parsing(date)

                try:
                    events = await self.get_events_by_exact_date(
                        date=date.strftime("%Y-%m-%d"),
                        cur=cur,
                    )
                except (ParserError, AttributeError):
                    embed = discord.Embed(
                        title="Incorrect Date Format",
                        description=f"Failed to parse given date: `{date}`",
                    )

                    await ctx.send(embed=embed)
                    return

            try:
                if len(events) == 1:
                    embed = await self.setlist_embed(
                        event=events[0],
                        ctx=ctx,
                        cur=cur,
                    )

                    await ctx.send(embed=embed)
                else:
                    menu = await viewmenu.create_view_menu(
                        ctx=ctx,
                        style="Event $ of &",
                    )

                    embeds = [
                        await self.setlist_embed(event=event, ctx=ctx, cur=cur)
                        for event in events
                    ]

                    menu.add_pages(embeds)

                    await menu.start()

            except (UnboundLocalError, reactionmenu.errors.NoPages):
                embed = await bot_embed.not_found_embed(
                    command=self.__class__.__name__,
                    message=date,
                )

                await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """Load extension into bot."""
    await bot.add_cog(Setlist(bot))
