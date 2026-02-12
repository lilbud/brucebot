import asyncio
import logging
import os
import re
import sys
from pathlib import Path

import discord
from cogs._help import MyHelp
from cogs.bot_stuff import db
from discord.ext import commands
from dotenv import load_dotenv

COGS_PATH = os.path.join(os.path.dirname(__file__), "cogs")
# COGS_PATH = Path(__file__).parent / "cogs"


class BruceBot(commands.Bot):
    """Custom Discord.py Bot implementation."""

    logging.basicConfig(format="%(message)s", level=logging.INFO)

    def __init__(self, prefix: str, ext_dir: Path) -> None:
        """Initialize custom bot."""
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(command_prefix=prefix, intents=intents, case_insensitive=True)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.ext_dir = ext_dir
        self.testing_channel = [1250545846160982047]
        self.testing_server = 735698850802565171

    async def load_extensions(self) -> None:
        """Load cogs from specified cog folder."""
        if not self.ext_dir.is_dir():
            logging.info("Extension directory %s does not exist.", self.ext_dir)
            return
        for filename in self.ext_dir.iterdir():
            if filename.suffix == ".py" and not filename.name.startswith("_"):
                try:
                    await self.load_extension(f"cogs.{filename.stem}")
                    self.logger.info("Loaded extension %s", filename.stem)
                except commands.ExtensionError:
                    self.logger.exception("Failed to load extension %s", filename.stem)

    async def on_ready(self) -> None:
        """Send when bot is online and ready."""
        self.logger.info("Logged in as %s", self.user)

    async def close(self) -> None:
        """Close bot on keyboard interrupt."""
        await super().close()
        await self.pool.close()

    async def setup_hook(self) -> None:
        """Load cogs from directory."""
        await self.load_extensions()

        # opening connection pool to database
        self.pool = await db.create_pool()
        await self.pool.open()

    async def on_message(self, message: discord.Message) -> None:
        """When message sent."""
        # if message:
        #     await message.channel.send("<@Travis_Bickle>")

        if message.author.bot:  # If the message is sent by a bot, return
            return

        # checks for only one instance of a prefix character
        if not re.search(r"!\w", message.content):
            return

        await self.process_commands(message)

    async def run_bot(self) -> None:
        """Run bot using provided token."""
        load_dotenv()
        try:
            await self.start(token=str(os.getenv("BOT_TOKEN")))
        except (
            discord.LoginFailure,
            KeyboardInterrupt,
            asyncio.exceptions.CancelledError,
        ):
            self.logger.info("Exiting...")
            await self.close()
            sys.exit(0)


# psycopg requires this while using a AsyncConnectionPool
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

bot = BruceBot(prefix="!", ext_dir=Path(Path(__file__).parent, "cogs"))

attributes = {"name": "bhelp"}

bot.help_command = MyHelp(command_attrs=attributes)


asyncio.run(bot.run_bot())
