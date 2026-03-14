import aiosqlite
import json

# Default DB file used by the bot (matches existing db file if present)
DB_PATH = 'ghw.db'


async def init_db(db_path: str = DB_PATH) -> None:
    """Create database and required tables for workshops and services."""
    async with aiosqlite.connect(db_path) as db:
        # Workshops: flows that correspond to "TALLER"
        await db.execute("""
        CREATE TABLE IF NOT EXISTS workshops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            created_at TEXT DEFAULT (datetime('now'))
        )
        """)

        # Services: flows that correspond to "SERVICIO"
        await db.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            created_at TEXT DEFAULT (datetime('now'))
        )
        """)

        # Generic checklist items: owner_type indicates workshop/service
        await db.execute("""
        CREATE TABLE IF NOT EXISTS checklist_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_type TEXT,
            owner_id INTEGER,
            item_index INTEGER,
            item_text TEXT
        )
        """)

        await db.commit()


async def insert_workshop(workflow: dict, user_id: int | None = None, db_path: str = DB_PATH) -> int:
    """Insert a `TALLER` workflow into `workshops` and its checklist items."""
    async with aiosqlite.connect(db_path) as db:
        # If legacy table `taller_outputs` exists, insert there for compatibility
        res = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='taller_outputs'")
        exists = await res.fetchone()
        # Build checklist JSON from selected indices
        selected = sorted(workflow.get('selected_indices', []))
        items = workflow.get('current_items', []) or []
        checklist_list = [items[idx] for idx in selected if 0 <= idx < len(items)]

        if exists:
            cur = await db.execute(
                "INSERT INTO taller_outputs (machine_name,machine_number,component,subcomponent,checklist,comments,panas) VALUES (?,?,?,?,?,?,?)",
                (
                    workflow.get('machine_name'),
                    workflow.get('machine_num') or workflow.get('machine_number'),
                    workflow.get('component_id') or workflow.get('component'),
                    workflow.get('subcomponent_id') or workflow.get('subcomponent'),
                    json.dumps(checklist_list),
                    workflow.get('comment'),
                    workflow.get('panas'),
                )
            )
            await db.commit()
            wid = cur.lastrowid
            return wid

        # Fallback to new `workshops` table
        cur = await db.execute(
            """
            INSERT INTO workshops (user_id,machine_name,machine_num,component_id,subcomponent_id,start_ts,end_ts,comment,panas,data_json)
            VALUES (?,?,?,?,?,?,?,?,?,?)
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
                json.dumps(workflow)
            )
        )
        await db.commit()
        wid = cur.lastrowid

        for idx in selected:
            if 0 <= idx < len(items):
                await db.execute("INSERT INTO checklist_items (owner_type,owner_id,item_index,item_text) VALUES (?,?,?,?)",
                                 ('workshop', wid, idx, items[idx]))

        await db.commit()
        return wid


async def insert_service(workflow: dict, user_id: int | None = None, db_path: str = DB_PATH) -> int:
    """Insert a `SERVICIO` workflow into `services` and its checklist items."""
    async with aiosqlite.connect(db_path) as db:
        # If legacy table `servicio_outputs` exists, insert there for compatibility
        res = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='servicio_outputs'")
        exists = await res.fetchone()

        selected = sorted(workflow.get('selected_indices', []))
        items = workflow.get('current_items', []) or []

        if exists:
            cur = await db.execute(
                "INSERT INTO servicio_outputs (client_name,service,subservice,details,horometro_inicio,horometro_termino,hectareas,comments,panas) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    workflow.get('client'),
                    workflow.get('service'),
                    workflow.get('subservice'),
                    json.dumps(workflow.get('details', {})),
                    workflow.get('horometro_inicio'),
                    workflow.get('horometro_termino'),
                    workflow.get('hectareas'),
                    workflow.get('comment'),
                    workflow.get('panas'),
                )
            )
            await db.commit()
            sid = cur.lastrowid
            return sid

        # Fallback to new `services` table
        cur = await db.execute(
            """
            INSERT INTO services (user_id,client_id,service_id,subservice_id,details_json,horometro_start,horometro_end,hectareas,comment,panas,start_ts,end_ts,data_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
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
                json.dumps(workflow)
            )
        )
        await db.commit()
        sid = cur.lastrowid

        for idx in selected:
            if 0 <= idx < len(items):
                await db.execute("INSERT INTO checklist_items (owner_type,owner_id,item_index,item_text) VALUES (?,?,?,?)",
                                 ('service', sid, idx, items[idx]))

        await db.commit()
        return sid


async def insert_workflow(workflow: dict, user_id: int | None = None, db_path: str = DB_PATH) -> int:
    """Compatibility wrapper: route to the correct insert function based on workflow['type']."""
    typ = (workflow.get('type') or '').upper()
    if typ == 'TALLER':
        return await insert_workshop(workflow, user_id=user_id, db_path=db_path)
    elif typ == 'SERVICIO':
        return await insert_service(workflow, user_id=user_id, db_path=db_path)
    else:
        # fallback: store in services table as generic
        return await insert_service(workflow, user_id=user_id, db_path=db_path)


async def insert_workflow_with_retry(workflow: dict, user_id: int | None = None, db_path: str = DB_PATH, retries: int = 3, delay: float = 0.1):
    """Attempt to insert workflow with simple retry logic for transient errors."""
    import asyncio as _asyncio
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            return await insert_workflow(workflow, user_id=user_id, db_path=db_path)
        except Exception as e:
            last_exc = e
            try:
                _asyncio.get_running_loop()
                await _asyncio.sleep(delay)
            except Exception:
                # if no loop, block sleep
                import time as _time
                _time.sleep(delay)
    # all attempts failed
    raise last_exc


async def _migrate_json_table(db, table_name: str, data: list, id_field: str = '_id'):
    """Helper to insert list of dicts into a simple key/value table."""
    await db.execute(f"CREATE TABLE IF NOT EXISTS {table_name} (id TEXT PRIMARY KEY, data_json TEXT)")
    for doc in data:
        key = doc.get(id_field) or doc.get('id') or doc.get('name')
        await db.execute(f"INSERT OR REPLACE INTO {table_name} (id,data_json) VALUES (?,?)", (str(key), json.dumps(doc, ensure_ascii=False)))


async def migrate_json_files_to_db(db_path: str = DB_PATH) -> None:
    """Load `clients.json` and `components.json` into DB tables if present."""
    import os
    async with aiosqlite.connect(db_path) as db:
        # clients.json -> structured clients table
        clients_file = os.path.join(os.getcwd(), 'clients.json')
        if os.path.exists(clients_file):
            try:
                with open(clients_file, 'r', encoding='utf-8') as f:
                    clients_obj = json.load(f)
                clients_list = clients_obj.get('clients') or []
                # If an existing clients table with different schema exists, adapt insert strategy
                res = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clients'")
                exists = await res.fetchone()
                if not exists:
                    await db.execute("CREATE TABLE IF NOT EXISTS clients (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)")
                    for name in clients_list:
                        try:
                            await db.execute("INSERT OR IGNORE INTO clients (name) VALUES (?)", (name,))
                        except Exception:
                            continue
                else:
                    # inspect columns
                    info = await db.execute("PRAGMA table_info(clients)")
                    cols = [r[1] for r in await info.fetchall()]
                    if 'name' in cols:
                        for name in clients_list:
                            try:
                                await db.execute("INSERT OR IGNORE INTO clients (name) VALUES (?)", (name,))
                            except Exception:
                                continue
                    else:
                        # legacy simple table (id TEXT PRIMARY KEY, data_json TEXT) — store as id=name
                        await db.execute("CREATE TABLE IF NOT EXISTS clients (id TEXT PRIMARY KEY, data_json TEXT)")
                        for name in clients_list:
                            try:
                                await db.execute("INSERT OR REPLACE INTO clients (id,data_json) VALUES (?,?)", (str(name), json.dumps({'name': name}, ensure_ascii=False)))
                            except Exception:
                                continue
            except Exception:
                pass

        # components.json -> unified components table (id, name, parent_id, tasks_json)
        comps_file = os.path.join(os.getcwd(), 'components.json')
        if os.path.exists(comps_file):
            try:
                with open(comps_file, 'r', encoding='utf-8') as f:
                    comps = json.load(f)
                colecciones = comps.get('colecciones', [])
                # handle existing components table variants
                res = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='components'")
                exists = await res.fetchone()
                if not exists:
                    await db.execute("CREATE TABLE IF NOT EXISTS components (id TEXT PRIMARY KEY, name TEXT, parent_id TEXT, tasks_json TEXT)")
                    for col in colecciones:
                        nombre = col.get('nombre', '').lower()
                        documentos = col.get('documentos', [])
                        if 'principales' in nombre:
                            for doc in documentos:
                                _id = doc.get('_id')
                                nombre_doc = doc.get('nombre')
                                tareas = doc.get('tareas')
                                await db.execute("INSERT OR REPLACE INTO components (id,name,parent_id,tasks_json) VALUES (?,?,?,?)", (_id, nombre_doc, None, json.dumps(tareas, ensure_ascii=False)))
                        elif 'secundarios' in nombre:
                            for doc in documentos:
                                _id = doc.get('_id')
                                nombre_doc = doc.get('nombre')
                                parent = doc.get('pertenece_a')
                                tareas = doc.get('tareas')
                                await db.execute("INSERT OR REPLACE INTO components (id,name,parent_id,tasks_json) VALUES (?,?,?,?)", (_id, nombre_doc, parent, json.dumps(tareas, ensure_ascii=False)))
                else:
                    info = await db.execute("PRAGMA table_info(components)")
                    cols = [r[1] for r in await info.fetchall()]
                    if 'name' in cols and 'tasks_json' in cols:
                        # modern schema
                        for col in colecciones:
                            nombre = col.get('nombre', '').lower()
                            documentos = col.get('documentos', [])
                            if 'principales' in nombre:
                                for doc in documentos:
                                    _id = doc.get('_id')
                                    nombre_doc = doc.get('nombre')
                                    tareas = doc.get('tareas')
                                    await db.execute("INSERT OR REPLACE INTO components (id,name,parent_id,tasks_json) VALUES (?,?,?,?)", (_id, nombre_doc, None, json.dumps(tareas, ensure_ascii=False)))
                            elif 'secundarios' in nombre:
                                for doc in documentos:
                                    _id = doc.get('_id')
                                    nombre_doc = doc.get('nombre')
                                    parent = doc.get('pertenece_a')
                                    tareas = doc.get('tareas')
                                    await db.execute("INSERT OR REPLACE INTO components (id,name,parent_id,tasks_json) VALUES (?,?,?,?)", (_id, nombre_doc, parent, json.dumps(tareas, ensure_ascii=False)))
                    else:
                        # legacy simple storage: id, data_json
                        await db.execute("CREATE TABLE IF NOT EXISTS components (id TEXT PRIMARY KEY, data_json TEXT)")
                        for col in colecciones:
                            documentos = col.get('documentos', [])
                            for doc in documentos:
                                _id = doc.get('_id') or doc.get('id') or doc.get('nombre')
                                try:
                                    await db.execute("INSERT OR REPLACE INTO components (id,data_json) VALUES (?,?)", (str(_id), json.dumps(doc, ensure_ascii=False)))
                                except Exception:
                                    continue
            except Exception:
                pass

        await db.commit()

        # After inserting/importing, normalize schemas for components and clients
        try:
            await _migrate_components_schema(db)
        except Exception:
            pass
        try:
            await _migrate_clients_schema(db)
        except Exception:
            pass


async def get_recent_taller_outputs(limit: int = 50, db_path: str = DB_PATH):
    async with aiosqlite.connect(db_path) as db:
        try:
            # prefer legacy `taller_outputs` when present, otherwise read from `workshops`
            res = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='taller_outputs'")
            if await res.fetchone():
                cur = await db.execute('SELECT * FROM taller_outputs ORDER BY id DESC LIMIT ?', (limit,))
                rows = await cur.fetchall()
                info = await db.execute("PRAGMA table_info(taller_outputs)")
                cols = [r[1] for r in await info.fetchall()]
                return [dict(zip(cols, row)) for row in rows]
            else:
                cur = await db.execute('SELECT * FROM workshops ORDER BY id DESC LIMIT ?', (limit,))
                rows = await cur.fetchall()
                info = await db.execute("PRAGMA table_info(workshops)")
                cols = [r[1] for r in await info.fetchall()]
                return [dict(zip(cols, row)) for row in rows]
        except Exception:
            return []


async def _migrate_components_schema(db):
    """Normalize `components` table into structured columns: id, name, parent_id, tasks_json.
    Handles legacy `components(id, data_json)` or mixed schemas.
    """
    info = await db.execute("PRAGMA table_info(components)")
    cols = [r[1] for r in await info.fetchall()]
    # If components table doesn't exist, nothing to do
    if not cols:
        return
    # If table already structured with name/tasks_json, nothing to do
    if 'name' in cols and 'tasks_json' in cols:
        return

    # Create new structured table
    await db.execute("CREATE TABLE IF NOT EXISTS components_new (id TEXT PRIMARY KEY, name TEXT, parent_id TEXT, tasks_json TEXT)")

    # If legacy columns are id, data_json
    if 'data_json' in cols:
        cur = await db.execute('SELECT id, data_json FROM components')
        rows = await cur.fetchall()
        for _id, data_json in rows:
            try:
                doc = json.loads(data_json) if data_json else {}
            except Exception:
                doc = {}
            comp_id = doc.get('_id') or _id
            name = doc.get('nombre') or doc.get('name') or comp_id
            parent = doc.get('pertenece_a') or doc.get('parent_id')
            tasks = doc.get('tareas') or doc.get('tasks')
            await db.execute("INSERT OR REPLACE INTO components_new (id,name,parent_id,tasks_json) VALUES (?,?,?,?)", (str(comp_id), name, parent, json.dumps(tasks, ensure_ascii=False) if tasks is not None else None))
    else:
        # Unknown legacy shape: copy whatever columns map to id/name if possible
        cur = await db.execute("SELECT * FROM components")
        rows = await cur.fetchall()
        info = await db.execute("PRAGMA table_info(components)")
        old_cols = [r[1] for r in await info.fetchall()]
        for row in rows:
            rowd = dict(zip(old_cols, row))
            comp_id = rowd.get('id') or rowd.get('_id') or rowd.get('codigo')
            name = rowd.get('name') or rowd.get('nombre') or comp_id
            parent = rowd.get('parent_id') or rowd.get('pertenece_a')
            tasks = rowd.get('tasks_json') or rowd.get('tareas') or rowd.get('tasks') or None
            await db.execute("INSERT OR REPLACE INTO components_new (id,name,parent_id,tasks_json) VALUES (?,?,?,?)", (str(comp_id), name, parent, json.dumps(tasks, ensure_ascii=False) if tasks is not None else None))

    # Replace old table
    await db.execute("DROP TABLE IF EXISTS components")
    await db.execute("ALTER TABLE components_new RENAME TO components")
    await db.commit()


async def _migrate_clients_schema(db):
        """Normalize `clients` table into structured columns: id INTEGER PK AUTOINCREMENT, name TEXT UNIQUE.
        Handles legacy `clients(id TEXT, data_json TEXT)` and other variants.
        """
        info = await db.execute("PRAGMA table_info(clients)")
        cols = [r[1] for r in await info.fetchall()]
        # If table doesn't exist, nothing to do
        if not cols:
            return
        # If already has name column and integer id column type, assume migrated
        info_rows = await (await db.execute("PRAGMA table_info(clients)")).fetchall()
        types = [r[2] for r in info_rows]
        if 'name' in cols and any(t and t.upper().startswith('INT') for t in types):
            return

        # Create new clients table
        await db.execute("CREATE TABLE IF NOT EXISTS clients_new (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)")

        if 'data_json' in cols:
            cur = await db.execute('SELECT id, data_json FROM clients')
            rows = await cur.fetchall()
            for _id, data_json in rows:
                try:
                    doc = json.loads(data_json) if data_json else {}
                except Exception:
                    doc = {}
                name = doc.get('name') or doc.get('nombre') or str(_id)
                try:
                    await db.execute("INSERT OR IGNORE INTO clients_new (name) VALUES (?)", (name,))
                except Exception:
                    continue
        elif 'name' in cols:
            cur = await db.execute('SELECT name FROM clients')
            rows = await cur.fetchall()
            for (name,) in rows:
                try:
                    await db.execute("INSERT OR IGNORE INTO clients_new (name) VALUES (?)", (name,))
                except Exception:
                    continue
        else:
            # Fallback: read whatever first text-like column could be name
            cur = await db.execute('SELECT * FROM clients')
            rows = await cur.fetchall()
            info = await db.execute('PRAGMA table_info(clients)')
            old_cols = [r[1] for r in await info.fetchall()]
            name_col = None
            for c in old_cols:
                if c.lower() in ('name', 'nombre', 'client'):
                    name_col = c
                    break
            for row in rows:
                rowd = dict(zip(old_cols, row))
                name = rowd.get(name_col) if name_col else str(rowd.get(old_cols[0]))
                try:
                    await db.execute("INSERT OR IGNORE INTO clients_new (name) VALUES (?)", (name,))
                except Exception:
                    continue

        # Replace old clients table
        await db.execute("DROP TABLE IF EXISTS clients")
        await db.execute("ALTER TABLE clients_new RENAME TO clients")
        await db.commit()


def get_clients_sync(db_path: str = DB_PATH):
    """Synchronous helper used at module import time to load client names from the DB.
    Returns a list of client names (strings)."""
    import sqlite3, os
    p = db_path
    if not os.path.exists(p):
        return []
    try:
        conn = sqlite3.connect(p)
        cur = conn.cursor()
        cur.execute("SELECT name FROM clients ORDER BY id")
        rows = cur.fetchall()
        conn.close()
        return [r[0] for r in rows if r and r[0]]
    except Exception:
        return []


def get_components_sync(db_path: str = DB_PATH):
    """Synchronous helper to load components from DB and return a structure
    similar to the original `components.json` format: {'colecciones': [...]}
    """
    import sqlite3, os
    p = db_path
    if not os.path.exists(p):
        return {}
    try:
        conn = sqlite3.connect(p)
        cur = conn.cursor()
        cur.execute("SELECT id,name,parent_id,tasks_json FROM components")
        rows = cur.fetchall()
        conn.close()

        principales = []
        secundarios = []
        for _id, name, parent, tasks_json in rows:
            doc = {'_id': _id, 'nombre': name}
            try:
                tareas = json.loads(tasks_json) if tasks_json else None
            except Exception:
                tareas = None
            if tareas is not None:
                doc['tareas'] = tareas
            if parent:
                doc['pertenece_a'] = parent
                secundarios.append(doc)
            else:
                principales.append(doc)

        colecciones = []
        if principales:
            colecciones.append({'nombre': 'componentes_principales', 'documentos': principales})
        if secundarios:
            colecciones.append({'nombre': 'componentes_secundarios', 'documentos': secundarios})

        return {'colecciones': colecciones}
    except Exception:
        return {}


async def get_recent_servicio_outputs(limit: int = 50, db_path: str = DB_PATH):
    async with aiosqlite.connect(db_path) as db:
        try:
            res = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='servicio_outputs'")
            if await res.fetchone():
                cur = await db.execute('SELECT * FROM servicio_outputs ORDER BY id DESC LIMIT ?', (limit,))
                rows = await cur.fetchall()
                info = await db.execute("PRAGMA table_info(servicio_outputs)")
                cols = [r[1] for r in await info.fetchall()]
                return [dict(zip(cols, row)) for row in rows]
            else:
                cur = await db.execute('SELECT * FROM services ORDER BY id DESC LIMIT ?', (limit,))
                rows = await cur.fetchall()
                info = await db.execute("PRAGMA table_info(services)")
                cols = [r[1] for r in await info.fetchall()]
                return [dict(zip(cols, row)) for row in rows]
        except Exception:
            return []
