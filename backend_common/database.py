# database.py
import datetime
import uuid
import os
import asyncpg
from asyncpg.pool import Pool
from typing import Optional, List
from contextlib import asynccontextmanager
import time
from backend_common.logging_wrapper import apply_decorator_to_module

from backend_common.logger import logging

logger = logging.getLogger(__name__)


class Database:
    pool: Optional[Pool] = None
    last_refresh_time: float = 0
    refresh_interval: int = 3600  # Refresh every hour
    time.sleep(5)
    dsn: str = os.getenv("DATABASE_URL")

    @classmethod
    async def create_pool(cls):
        """
        Creates a new connection pool with specified configuration.
        
        Sets up an asyncpg connection pool with min_size=1 and max_size=10.
        Updates the last refresh time after creation.
        """
        cls.pool = await asyncpg.create_pool(dsn=cls.dsn, min_size=1, max_size=10)
        cls.last_refresh_time = time.time()

    @classmethod
    async def close_pool(cls):
        """
        Closes the existing connection pool if it exists.
        Sets the pool reference to None after closing.
        """
        if cls.pool:
            await cls.pool.close()
        cls.pool = None

    @classmethod
    async def get_pool(cls):
        """
        Retrieves the current connection pool or creates a new one.
        
        If the pool doesn't exist, creates a new one.
        If the pool exists but is older than refresh_interval, refreshes it.
        
        Returns:
            Pool: The current database connection pool
        """
        if not cls.pool:
            await cls.create_pool()
        elif time.time() - cls.last_refresh_time > cls.refresh_interval:
            await cls.refresh_pool()
        return cls.pool

    @classmethod
    async def refresh_pool(cls):
        """
        Refreshes the connection pool by creating a new one and closing the old one.
        Prints a message indicating the refresh operation.
        """
        print("Refreshing connection pool...")
        old_pool = cls.pool
        await cls.create_pool()
        await old_pool.close()

    @classmethod
    @asynccontextmanager
    async def connection(cls):
        """
        Context manager for acquiring a connection from the pool.
        
        Yields:
            Connection: A database connection from the pool
        """
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            yield conn

    @classmethod
    async def fetch(cls, query: str, *args):
        """
        Executes a query and returns all results.
        
        Args:
            query: SQL query string
            *args: Query parameters
        
        Returns:
            List[Record]: List of all matching records
        """
        logger.info(f"Executing fetch query: {cls.generate_sql_script(query, *args)}")
        async with cls.connection() as conn:
            return await conn.fetch(query, *args)

    @classmethod
    async def fetchrow(cls, query: str, *args):
        """
        Executes a query and returns the first result.
        
        Args:
            query: SQL query string
            *args: Query parameters
        
        Returns:
            Record: First matching record or None
        """
        logger.info(f"Executing fetchrow query: {cls.generate_sql_script(query, *args)}")
        async with cls.connection() as conn:
            return await conn.fetchrow(query, *args)

    @classmethod
    async def execute(cls, query: str, *args, save_sql_script: bool = False):
        """
        Executes a query with optional SQL script saving.
        
        Args:
            query: SQL query string
            *args: Query parameters
            save_sql_script: If True, saves the generated SQL script to a file
        
        Returns:
            str: Command completion tag
        """
        formatted_query = cls.generate_sql_script(query, *args)
        logger.info(f"Executing query: {formatted_query}")
        async with cls.connection() as conn:
            if save_sql_script:
                unique_id = str(uuid.uuid4())[:8]
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                sql_script = cls.generate_sql_script(query, *args)
                filename = f"sql_script_{timestamp}_{unique_id}.sql"
                cls.save_sql_script(filename, sql_script)
            return await conn.execute(query, *args)

    @classmethod
    async def execute_many(cls, query: str, entries: List[list]):
        """
        Executes a query multiple times with different parameters.
        
        Args:
            query: SQL query string
            entries: List of parameter lists for multiple executions
        
        Returns:
            List[str]: List of command completion tags
        """
        logger.info(f"Executing many queries with template: {query}")
        logger.debug(f"First few entries: {entries[:3]}")  # Log just first few entries to avoid overwhelming logs
        async with cls.connection() as conn:
            return await conn.executemany(query, entries)

    @staticmethod
    def generate_sql_script(query: str, *args) -> str:
        """
        Generates a SQL script by replacing placeholders with actual values.
        
        Args:
            query: SQL query string with placeholders
            *args: Values to replace placeholders
        
        Returns:
            str: SQL query with replaced values
        """
        for i, arg in enumerate(args, start=1):
            placeholder = f"${i}"
            if isinstance(arg, str):
                escaped_arg = arg.replace("'", "''")
                query = query.replace(placeholder, f"'{escaped_arg}'", 1)
            else:
                query = query.replace(placeholder, str(arg), 1)
        return query

    @staticmethod
    def save_sql_script(filename: str, content: str):
        """
        Saves a SQL script to a file in the sql_scripts directory.
        
        Args:
            filename: Name of the file to save
            content: SQL script content
        """
        os.makedirs("sql_scripts", exist_ok=True)
        with open(os.path.join("sql_scripts", filename), "w") as f:
            f.write(content)
        print(f"SQL script saved as {filename}")

    @classmethod
    @asynccontextmanager
    async def transaction(cls):
        """
        Context manager for database transactions.
        
        Yields:
            Connection: A database connection within a transaction
        """
        async with cls.connection() as conn:
            async with conn.transaction():
                yield conn

    @classmethod
    async def health_check(cls):
        """
        Performs a health check on the database connection.
        
        Returns:
            bool: True if the connection is healthy, False otherwise
        """
        try:
            async with cls.connection() as conn:
                await conn.execute("SELECT 1")
            return True
        except Exception:
            return False


# Apply the decorator to all functions in this module
apply_decorator_to_module(logger)(__name__)
