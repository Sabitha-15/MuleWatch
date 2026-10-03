import os

import psycopg
from dotenv import load_dotenv


load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    """
    Create and return a PostgreSQL database connection.
    """

    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not configured."
        )

    return psycopg.connect(DATABASE_URL)