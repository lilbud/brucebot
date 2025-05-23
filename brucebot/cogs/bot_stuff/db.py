import os
import sys

from dotenv import load_dotenv
from psycopg_pool import AsyncConnectionPool


async def create_pool() -> AsyncConnectionPool:
    """Create a connection pool for the database."""
    load_dotenv()

    match sys.argv[2]:
        case "local":
            return AsyncConnectionPool(conninfo=os.getenv("LOCAL_DB_URL"), open=False)
        case "heroku":
            return AsyncConnectionPool(
                conninfo=os.getenv("HEROKU_DATABASE_URL"),
                open=False,
            )
        case "supabase":
            return AsyncConnectionPool(
                conninfo=os.getenv("SUPABASE_DATABASE_URL"),
                open=False,
            )
