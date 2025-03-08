import datetime
import re
from urllib.parse import urlparse

import discord
from dateutil import parser


async def date_parsing(date: str) -> datetime.datetime | Exception:
    """Input date parsing.

    Attempt to parse the provided the date into a Python datetime object.
    If parsing fails, return the input. The cog will usually throw its
    own error if date is required.
    """
    try:
        return parser.parse(date).date()
    except parser.ParserError as e:
        return e


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


async def clean_message(argument: str) -> str:
    """Remove apostrophes."""
    replacements = [("’", "''"), ("‘", "''"), ("”", '"'), ("‟", '"')]

    for pattern, repl in replacements:
        argument = re.sub(pattern, repl, argument)

    return argument
