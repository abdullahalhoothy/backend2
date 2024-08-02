# database.py
import asyncio
import asyncpg
from asyncpg.pool import Pool
from typing import Optional
from contextlib import asynccontextmanager
import time
import json
import uuid

class Database:
    pool: Optional[Pool] = None
    last_refresh_time: float = 0
    refresh_interval: int = 3600  # Refresh every hour
    dsn: str = "postgresql://scraper_user:scraper_password@s-locator.northernacs.com:5432/aqar_scraper"

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
    async def execute(cls, query: str, *args):
        async with cls.connection() as conn:
            return await conn.execute(query, *args)

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
        
    @classmethod
    async def create_riyadh_villa_allrooms_json_table(cls):
        create_table_query = """
        CREATE TABLE IF NOT EXISTS riyadh_villa_allrooms_json (
            id UUID PRIMARY KEY,
            data JSONB
        );
        """
        await cls.execute(create_table_query)

    @classmethod
    async def insert_json_data(cls, json_data: dict):
        insert_query = """
        INSERT INTO riyadh_villa_allrooms_json (id, data) 
        VALUES ($1, $2)
        """
        new_id = str(uuid.uuid4())
        json_str = json.dumps(json_data)  # Convert dict to JSON string
        await cls.execute(insert_query, new_id, json_str)
        return new_id
