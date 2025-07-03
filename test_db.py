import asyncio
from sqlalchemy import text
from app.database import async_engine


async def test_connection():
    try:
        async with async_engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("✅ PostgreSQL connection successful")
            return True
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(test_connection())
