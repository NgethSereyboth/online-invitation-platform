#!/usr/bin/env python3
from __future__ import annotations
import os, sqlite3, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
import sys;sys.path.insert(0,str(ROOT))
import backup_restore

def run():
    with tempfile.TemporaryDirectory(prefix='einvite-backup-source-') as source, tempfile.TemporaryDirectory(prefix='einvite-backup-out-') as out:
        os.environ['EINVITE_DATA_DIR']=source
        root=Path(source);(root/'uploads').mkdir();(root/'uploads'/'test.bin').write_bytes(b'hello-media')
        db=sqlite3.connect(root/'invites.db');db.execute('create table sample(id integer primary key,value text)');db.execute('insert into sample(value) values(?)',('hello',));db.commit();db.close()
        archive=Path(out)/'backup.zip';backup_restore.create_backup(archive);backup_restore.verify_backup(archive)
        dest=Path(out)/'restore';backup_restore.restore_backup(archive,dest)
        assert (dest/'uploads'/'test.bin').read_bytes()==b'hello-media'
        db=sqlite3.connect(dest/'invites.db');assert db.execute('select value from sample').fetchone()[0]=='hello';db.close()
    print('V13_BACKUP_RESTORE_TEST_PASSED')
if __name__=='__main__':run()
