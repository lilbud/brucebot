import datetime

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
    label: str = "",
) -> discord.ui.Button:
    """Create link button with provided URL."""
    return discord.ui.Button(
        style="link",
        url=url,
        label=label,
    )


async def song_find_fuzzy(
    query: str,
    cur: psycopg.AsyncCursor,
) -> dict:
    """Fuzzy search SONGS table using full text search."""
    res = await cur.execute(
        """
        WITH search_results AS (
            SELECT
                s.id,
                s.song_name,
                s.fts_name_vector,
                websearch_to_tsquery('english', %(query)s) AS q
            FROM
                songs s
            WHERE
                s.fts_name_vector @@ websearch_to_tsquery('english', %(query)s)
        )
        SELECT
            *
        FROM
            search_results sr
        ORDER BY
            extensions.SIMILARITY(%(query)s, sr.song_name) DESC,
            ts_rank(sr.fts_name_vector, q) DESC
        LIMIT 1;
        """,
        {"query": query},
    )

    return await res.fetchone()
