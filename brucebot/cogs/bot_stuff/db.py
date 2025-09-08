import os
import sys

import psycopg
from dotenv import load_dotenv
from psycopg_pool import AsyncConnectionPool


def load_db() -> psycopg.Connection:
    """Load DB and return connection."""
    load_dotenv()

    match sys.argv[2]:
        case "local":
            conninfo = os.getenv("LOCAL_DB_URL")

        case "heroku":
            conninfo = os.getenv("HEROKU_DATABASE_URL")

        case "supabase":
            conninfo = os.getenv("SUPABASE_DATABASE_URL")

        case "digitalocean":
            conninfo = os.getenv("DO_DATABASE_URL")

    return psycopg.connect(
        conninfo=conninfo,
    )


async def create_pool() -> AsyncConnectionPool:
    """Create a connection pool for the database."""
    load_dotenv()

    match sys.argv[2]:
        case "local":
            return AsyncConnectionPool(
                conninfo=os.getenv("LOCAL_DB_URL"),
                kwargs={"prepare_threshold": None},
                open=False,
            )
        case "heroku":
            return AsyncConnectionPool(
                conninfo=os.getenv("HEROKU_DATABASE_URL"),
                kwargs={"prepare_threshold": None},
                open=False,
            )
        case "supabase":
            return AsyncConnectionPool(
                conninfo=os.getenv("SUPABASE_DATABASE_URL"),
                kwargs={"prepare_threshold": None},
                open=False,
            )
        case "digitalocean":
            return AsyncConnectionPool(
                conninfo=os.getenv("DO_DATABASE_URL"),
                kwargs={"prepare_threshold": None},
                open=False,
            )
