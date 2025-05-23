import aiosqlite
import os

DB_PATH = os.getenv("DATABASE_PATH", "seen.db")

async def init_db():
    db = await aiosqlite.connect(DB_PATH)
    await db.execute("""
    CREATE TABLE IF NOT EXISTS seen_posts (
      post_id TEXT PRIMARY KEY,
      seen_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    await db.commit()
    return db

async def is_new(db, post_id: str) -> bool:
    cursor = await db.execute(
        "SELECT 1 FROM seen_posts WHERE post_id = ?", (post_id,)
    )
    row = await cursor.fetchone()
    return row is None

async def mark_seen(db, post_id: str):
    await db.execute(
        "INSERT INTO seen_posts (post_id) VALUES (?)", (post_id,)
    )
    await db.commit()