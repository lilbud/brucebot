import os

from dotenv import load_dotenv
from psycopg_pool import AsyncConnectionPool


async def create_pool(db: str) -> AsyncConnectionPool:
    """Create a connection pool for the database."""
    load_dotenv()

    match db:
        case "local":
            return AsyncConnectionPool(conninfo=os.getenv("LOCAL_DB_URL"), open=False)
        case "heroku":
            return AsyncConnectionPool(conninfo=os.getenv("DATABASE_URL"), open=False)
