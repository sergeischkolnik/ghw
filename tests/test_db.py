import asyncio
import os
import json
import tempfile
import unittest

from db import init_db, migrate_json_files_to_db, insert_workflow_with_retry, get_recent_taller_outputs, get_recent_servicio_outputs, DB_PATH

class DBTests(unittest.TestCase):
    def setUp(self):
        # use a temp DB file
        self.tmpdb = os.path.join(os.getcwd(), 'test_ghw.db')
        if os.path.exists(self.tmpdb):
            os.remove(self.tmpdb)

    def tearDown(self):
        if os.path.exists(self.tmpdb):
            os.remove(self.tmpdb)

    def test_init_and_migrate(self):
        asyncio.run(init_db(self.tmpdb))
        # migration should not fail even if files are absent
        asyncio.run(migrate_json_files_to_db(self.tmpdb))
        # insert a sample taller
        workflow = {
            'type': 'TALLER',
            'machine_name': 'TestMachine',
            'machine_num': '99',
            'component_id': 'CP001',
            'subcomponent_id': 'CS001',
            'selected_indices': [0],
            'current_items': ['check1'],
        }
        wid = asyncio.run(insert_workflow_with_retry(workflow, user_id=123, db_path=self.tmpdb))
        self.assertIsNotNone(wid)
        # insert a sample servicio
        workflow2 = {
            'type': 'SERVICIO',
            'client': 'UnitClient',
            'service': 'S01',
            'subservice': 'SS01',
            'details': {'hileras': 1},
        }
        sid = asyncio.run(insert_workflow_with_retry(workflow2, user_id=456, db_path=self.tmpdb))
        self.assertIsNotNone(sid)
        # fetch recent
        taller = asyncio.run(get_recent_taller_outputs(limit=5, db_path=self.tmpdb))
        servicio = asyncio.run(get_recent_servicio_outputs(limit=5, db_path=self.tmpdb))
        self.assertTrue(len(taller) >= 1)
        self.assertTrue(len(servicio) >= 1)

if __name__ == '__main__':
    unittest.main()
