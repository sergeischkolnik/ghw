import psycopg
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


def get_database_url():
    """Get DATABASE_URL from environment, with lazy loading."""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    return database_url


async def get_db_conn():
    """Get a PostgreSQL async connection."""
    db_url = get_database_url()
    return await psycopg.AsyncConnection.connect(db_url)


def convert_datetime_to_str(obj):
    """Recursively convert datetime objects to ISO format strings and sets to lists for JSON serialization."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, set):
        return [convert_datetime_to_str(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: convert_datetime_to_str(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetime_to_str(item) for item in obj]
    return obj


async def init_db() -> None:
    """Create required tables for workshops and services."""
    conn = await get_db_conn()
    try:
        # Workshops: flows that correspond to "TALLER"
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS workshops (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            machine_name TEXT,
            machine_num TEXT,
            component_id TEXT,
            subcomponent_id TEXT,
            start_ts TEXT,
            end_ts TEXT,
            comment TEXT,
            panas TEXT,
            data_json TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """)

        # Services: flows that correspond to "SERVICIO"
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            client_id TEXT,
            service_id TEXT,
            subservice_id TEXT,
            details_json TEXT,
            horometro_start TEXT,
            horometro_end TEXT,
            hectareas TEXT,
            comment TEXT,
            panas TEXT,
            start_ts TEXT,
            end_ts TEXT,
            data_json TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """)

        # Generic checklist items: owner_type indicates workshop/service
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS checklist_items (
            id SERIAL PRIMARY KEY,
            owner_type TEXT,
            owner_id INTEGER,
            item_index INTEGER,
            item_text TEXT
        )
        """)

        print("[DB] Tables created successfully", flush=True)
    finally:
        await conn.close()


async def insert_workshop(workflow: dict, user_id: int | None = None) -> int:
    """Insert a `TALLER` workflow into `workshops` and its checklist items."""
    conn = await get_db_conn()
    try:
        # Build checklist JSON from selected indices
        selected = sorted(workflow.get('selected_indices', []))
        items = workflow.get('current_items', []) or []

        # Convert datetime objects to strings for JSON serialization
        workflow_serializable = convert_datetime_to_str(workflow)
        
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO workshops (user_id,machine_name,machine_num,component_id,subcomponent_id,start_ts,end_ts,comment,panas,data_json)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
                """,
                (
                    user_id,
                    workflow.get('machine_name'),
                    workflow.get('machine_num'),
                    workflow.get('component_id'),
                    workflow.get('subcomponent_id'),
                    workflow.get('start').isoformat() if workflow.get('start') else None,
                    workflow.get('end').isoformat() if workflow.get('end') else None,
                    workflow.get('comment'),
                    workflow.get('panas'),
                    json.dumps(workflow_serializable)
                )
            )
            result = await cur.fetchone()
            wid = result[0] if result else None

            for idx in selected:
                if 0 <= idx < len(items):
                    await cur.execute(
                        "INSERT INTO checklist_items (owner_type,owner_id,item_index,item_text) VALUES (%s,%s,%s,%s)",
                        ('workshop', wid, idx, items[idx])
                    )

        return wid
    finally:
        await conn.close()


async def insert_service(workflow: dict, user_id: int | None = None) -> int:
    """Insert a `SERVICIO` workflow into `services` and its checklist items."""
    conn = await get_db_conn()
    try:
        selected = sorted(workflow.get('selected_indices', []))
        items = workflow.get('current_items', []) or []

        # Convert datetime objects to strings for JSON serialization
        workflow_serializable = convert_datetime_to_str(workflow)
        
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO services (user_id,client_id,service_id,subservice_id,details_json,horometro_start,horometro_end,hectareas,comment,panas,start_ts,end_ts,data_json)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
                """,
                (
                    user_id,
                    workflow.get('client'),
                    workflow.get('service'),
                    workflow.get('subservice'),
                    json.dumps(workflow.get('details', {})),
                    workflow.get('horometro_inicio'),
                    workflow.get('horometro_termino'),
                    workflow.get('hectareas'),
                    workflow.get('comment'),
                    workflow.get('panas'),
                    workflow.get('start').isoformat() if workflow.get('start') else None,
                    workflow.get('end').isoformat() if workflow.get('end') else None,
                    json.dumps(workflow_serializable)
                )
            )
            result = await cur.fetchone()
            sid = result[0] if result else None

            for idx in selected:
                if 0 <= idx < len(items):
                    await cur.execute(
                        "INSERT INTO checklist_items (owner_type,owner_id,item_index,item_text) VALUES (%s,%s,%s,%s)",
                        ('service', sid, idx, items[idx])
                    )

        return sid
    finally:
        await conn.close()


async def insert_workflow(workflow: dict, user_id: int | None = None) -> int:
    """Compatibility wrapper: route to the correct insert function based on workflow['type']."""
    typ = (workflow.get('type') or '').upper()
    if typ == 'TALLER':
        return await insert_workshop(workflow, user_id=user_id)
    elif typ == 'SERVICIO':
        return await insert_service(workflow, user_id=user_id)
    else:
        # fallback: store in services table as generic
        return await insert_service(workflow, user_id=user_id)


async def insert_workflow_with_retry(workflow: dict, user_id: int | None = None, retries: int = 3, delay: float = 0.1):
    """Attempt to insert workflow with simple retry logic for transient errors."""
    import asyncio as _asyncio
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            return await insert_workflow(workflow, user_id=user_id)
        except Exception as e:
            last_exc = e
            try:
                await _asyncio.sleep(delay)
            except Exception:
                import time as _time
                _time.sleep(delay)
    # all attempts failed
    raise last_exc
