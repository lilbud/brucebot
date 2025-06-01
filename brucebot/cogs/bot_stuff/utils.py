import datetime
from urllib.parse import urlparse

import dateparser
import discord
import psycopg
from dateutil import parser


async def date_parsing(date: str) -> datetime.datetime | str:
    """Input date parsing.

    Attempt to parse the provided the date into a Python datetime object.
    If parsing fails, return the input. The cog will usually throw its
    own error if date is required.
    """
    try:
        return dateparser.parse(date).date()
    except (parser.ParserError, AttributeError):
        return date


async def format_link(url: str, text: str) -> str:
    """Format link as markdown.

    Returns a short link in markdown format given a url and text.
    """
    return f"[{text}](<{url}>)"


async def create_link_button(
    url: str,
) -> discord.ui.Button:
    """Create link button with provided URL."""
    return discord.ui.Button(
        style="link",
        url=url,
        label=urlparse(url).netloc,
    )


async def song_find_fuzzy(
    query: str,
    cur: psycopg.AsyncCursor,
) -> dict:
    """Fuzzy search SONGS table using full text search."""
    res = await cur.execute(
        """
        SELECT
            s.id,
            s.brucebase_url,
            s.song_name,
            rank,
            similarity
        FROM
            "songs" s,
            plainto_tsquery('simple', %(query)s) query,
            ts_rank(fts, query) rank,
            extensions.extensions.SIMILARITY(coalesce(aliases, '') || ' ' || coalesce(short_name, '') || ' ' || song_name, %(query)s) similarity
        WHERE query @@ fts
        AND similarity >= 0.0415
        ORDER BY similarity DESC, rank DESC NULLS LAST LIMIT 1;
        """,  # noqa: E501
        {"query": query},
    )

    return await res.fetchone()
