"""Reset helpers only; disposable SQLite. Never loads private configuration."""
import os,sqlite3,tempfile,unittest
from pathlib import Path
from tools.reset_records import clear_records,private_write
class ResetTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.executescript("CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT); INSERT INTO settings VALUES('schema','2'),('mode','demo'),('model','synthetic'),('enrollment_plan','private test settings'); CREATE TABLE testers(id TEXT); INSERT INTO testers VALUES('fake'); CREATE TABLE events(id INTEGER); INSERT INTO events VALUES(1); CREATE TABLE unrelated(id INTEGER); INSERT INTO unrelated VALUES(1);")
    def tearDown(self):self.db.close()
    def test_clear_preserves_structure_and_compatibility_only(self):
        clear_records(self.db,['settings','testers','events'])
        self.assertEqual(self.db.execute('SELECT count(*) FROM testers').fetchone()[0],0)
        self.assertEqual(dict(self.db.execute('SELECT * FROM settings')),{'schema':'2','mode':'demo','model':'synthetic'})
        self.assertEqual(self.db.execute('SELECT count(*) FROM unrelated').fetchone()[0],1)
    def test_reset_transaction_rolls_back(self):
        self.db.execute('BEGIN')
        clear_records(self.db,['settings','testers','events']);self.db.rollback()
        self.assertEqual(self.db.execute('SELECT count(*) FROM testers').fetchone()[0],1)
    def test_local_snapshot_can_be_restored(self):
        snapshot='\n'.join(self.db.iterdump())
        clear_records(self.db,['settings','testers','events'])
        restored=sqlite3.connect(':memory:')
        try:
            restored.executescript(snapshot)
            self.assertEqual(restored.execute('SELECT count(*) FROM testers').fetchone()[0],1)
        finally:restored.close()
    def test_backup_is_private_and_never_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'records.sql';private_write(path,'synthetic')
            self.assertEqual(os.stat(path).st_mode & 0o777,0o600)
            with self.assertRaises(FileExistsError):private_write(path,'overwrite')
