#!/usr/bin/env python3
"""Initialize PostgreSQL database with required tables."""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

# Import the new db module
import db_postgres as db


async def main():
    print("🔧 Initializing PostgreSQL database...")
    try:
        await db.init_db()
        print("✅ Database initialized successfully!")
        print("Tables created:")
        print("  - workshops")
        print("  - services")
        print("  - checklist_items")
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
