# database.py
import datetime
import uuid
import os
import asyncpg
from asyncpg.pool import Pool
from typing import Optional
from contextlib import asynccontextmanager
import time

class Database:
    pool: Optional[Pool] = None
    last_refresh_time: float = 0
    refresh_interval: int = 3600  # Refresh every hour
    # dsn: str = os.getenv('DATABASE_URL')
    dsn: str = "postgresql://ahmed:pass@localhost:5432/aqar_scraper"

    @classmethod
    async def create_pool(cls):
        cls.pool = await asyncpg.create_pool(
            dsn=cls.dsn,
            min_size=1,
            max_size=10
        )
        cls.last_refresh_time = time.time()

    @classmethod
    async def close_pool(cls):
        if cls.pool:
            await cls.pool.close()
        cls.pool = None

    @classmethod
    async def get_pool(cls):
        if not cls.pool:
            await cls.create_pool()
        elif time.time() - cls.last_refresh_time > cls.refresh_interval:
            await cls.refresh_pool()
        return cls.pool

    @classmethod
    async def refresh_pool(cls):
        print("Refreshing connection pool...")
        old_pool = cls.pool
        await cls.create_pool()
        await old_pool.close()

    @classmethod
    @asynccontextmanager
    async def connection(cls):
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            yield conn

    @classmethod
    async def fetch(cls, query: str, *args):
        async with cls.connection() as conn:
            return await conn.fetch(query, *args)

    @classmethod
    async def fetchrow(cls, query: str, *args):
        async with cls.connection() as conn:
            return await conn.fetchrow(query, *args)

    @classmethod
    async def execute(cls, query: str, *args, save_sql_script: bool = False):
        async with cls.connection() as conn:
            if save_sql_script:
                unique_id = str(uuid.uuid4())[:8]
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                sql_script = cls.generate_sql_script(query, *args)
                filename = f"sql_script_{timestamp}_{unique_id}.sql"
                cls.save_sql_script(filename, sql_script)

            return await conn.execute(query, *args)

    @staticmethod
    def generate_sql_script(query: str, *args) -> str:
        # Replace placeholders with actual values
        for i, arg in enumerate(args, start=1):
            placeholder = f'${i}'
            if isinstance(arg, str):
                # Escape single quotes in the string and wrap in single quotes
                escaped_arg = arg.replace("'", "''")
                query = query.replace(placeholder, f"'{escaped_arg}'", 1)
            else:
                query = query.replace(placeholder, str(arg), 1)
        return query

    @staticmethod
    def save_sql_script(filename: str, content: str):
        os.makedirs('sql_scripts', exist_ok=True)
        with open(os.path.join('sql_scripts', filename), 'w') as f:
            f.write(content)
        print(f"SQL script saved as {filename}")

    @classmethod
    @asynccontextmanager
    async def transaction(cls):
        async with cls.connection() as conn:
            async with conn.transaction():
                yield conn

    @classmethod
    async def health_check(cls):
        try:
            async with cls.connection() as conn:
                await conn.execute("SELECT 1")
            return True
        except Exception:
            return False
   