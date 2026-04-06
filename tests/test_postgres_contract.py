import inspect

import db_postgres as db_postgres


def test_postgres_async_contract():
    required_async = [
        'init_db',
        'insert_workflow',
        'insert_workflow_with_retry',
        'get_recent_taller_outputs',
        'get_recent_servicio_outputs',
    ]

    for name in required_async:
        assert hasattr(db_postgres, name), f"Missing async function: {name}"
        assert inspect.iscoroutinefunction(getattr(db_postgres, name)), f"Expected coroutine function: {name}"


def test_postgres_sync_compat_contract():
    assert hasattr(db_postgres, 'get_components_sync')
    assert callable(db_postgres.get_components_sync)

    assert hasattr(db_postgres, 'get_clients_sync')
    assert callable(db_postgres.get_clients_sync)
