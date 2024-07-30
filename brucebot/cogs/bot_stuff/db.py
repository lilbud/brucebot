import os

from dotenv import load_dotenv
from psycopg_pool import AsyncConnectionPool


async def create_pool() -> AsyncConnectionPool:
    """Create a connection pool for the database."""
    load_dotenv()
    return AsyncConnectionPool(conninfo=os.getenv("HEROKU_DB_URL"), open=False)
