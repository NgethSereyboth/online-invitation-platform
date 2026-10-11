#!/usr/bin/env python3
"""Create and verify portable local backups for E-invitation-website.

For managed PostgreSQL/object storage, provider snapshots/versioning remain the primary
backup mechanism; this utility is a local/off-site export and restore-test helper.
"""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, sqlite3, subprocess, tempfile, time, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def data_dir():return Path(os.environ.get('EINVITE_DATA_DIR') or ROOT/'data').resolve()
def database_url():return str(os.environ.get('EINVITE_DATABASE_URL') or '').strip()
def is_postgres(url=None):return str(url if url is not None else database_url()).startswith(('postgres://','postgresql://'))

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def create_backup(output:Path):
    src=data_dir();output.parent.mkdir(parents=True,exist_ok=True);url=database_url()
    manifest={'createdAt':int(time.time()*1000),'format':2,'databaseKind':'postgresql' if is_postgres(url) else 'sqlite','files':[],'restoreVerified':False}
    with tempfile.TemporaryDirectory(prefix='einvite-backup-') as tmp:
        stage=Path(tmp)
        if is_postgres(url):
            pg_dump=shutil.which('pg_dump')
            if not pg_dump:raise RuntimeError('PostgreSQL backup requires pg_dump on PATH. Install the PostgreSQL client tools before creating a production database backup.')
            dest=stage/'postgres.dump'
            subprocess.run([pg_dump,'--format=custom','--no-owner','--no-privileges','--file',str(dest),url],check=True,stdout=subprocess.DEVNULL)
        else:
            db=src/'invites.db'
            if db.exists():
                dest=stage/'invites.db';source=sqlite3.connect(db);target=sqlite3.connect(dest);source.backup(target);target.close();source.close()
        for folder in ('uploads','image-cache'):
            media=src/folder
            if media.exists():shutil.copytree(media,stage/folder)
        for f in sorted(x for x in stage.rglob('*') if x.is_file()):manifest['files'].append({'path':f.relative_to(stage).as_posix(),'sha256':sha(f),'size':f.stat().st_size})
        (stage/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
            for f in stage.rglob('*'):
                if f.is_file():z.write(f,f.relative_to(stage).as_posix())
    return manifest

def verify_backup(archive:Path):
    with tempfile.TemporaryDirectory(prefix='einvite-restore-test-') as tmp:
        with zipfile.ZipFile(archive) as z:z.extractall(tmp)
        root=Path(tmp);manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
        for row in manifest['files']:
            f=root/row['path']
            if not f.is_file() or sha(f)!=row['sha256']:raise RuntimeError(f"Backup verification failed: {row['path']}")
        db=root/'invites.db'
        if db.exists():
            conn=sqlite3.connect(db);result=conn.execute('PRAGMA integrity_check').fetchone()[0];conn.close()
            if result!='ok':raise RuntimeError(f'SQLite restore integrity check failed: {result}')
        pg=root/'postgres.dump'
        if pg.exists():
            pg_restore=shutil.which('pg_restore')
            if not pg_restore:raise RuntimeError('PostgreSQL backup verification requires pg_restore on PATH.')
            subprocess.run([pg_restore,'--list',str(pg)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,encoding='utf-8')
        manifest['restoreVerified']=True
        return manifest

def restore_backup(archive:Path,destination:Path,force=False,postgres_url=''):
    if destination.exists() and any(destination.iterdir()) and not force:raise RuntimeError('Restore destination is not empty; use --force only for an intentional restore')
    manifest=verify_backup(archive);destination.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        names=set(z.namelist())
        for member in z.infolist():
            if member.filename in {'manifest.json','postgres.dump'}:continue
            z.extract(member,destination)
        if 'postgres.dump' in names:
            if not postgres_url:raise RuntimeError('This archive contains PostgreSQL data. Pass --postgres-url to perform an intentional database restore.')
            pg_restore=shutil.which('pg_restore')
            if not pg_restore:raise RuntimeError('PostgreSQL restore requires pg_restore on PATH.')
            with tempfile.TemporaryDirectory(prefix='einvite-pg-restore-') as tmp:
                dump=Path(tmp)/'postgres.dump';dump.write_bytes(z.read('postgres.dump'))
                subprocess.run([pg_restore,'--clean','--if-exists','--no-owner','--no-privileges','--dbname',postgres_url,str(dump)],check=True)
    return manifest

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='cmd',required=True)
    c=sub.add_parser('create');c.add_argument('output',type=Path)
    v=sub.add_parser('verify');v.add_argument('archive',type=Path)
    r=sub.add_parser('restore');r.add_argument('archive',type=Path);r.add_argument('destination',type=Path);r.add_argument('--force',action='store_true');r.add_argument('--postgres-url',default='',help='Target PostgreSQL URL when restoring a PostgreSQL archive')
    a=p.parse_args()
    if a.cmd=='create':create_backup(a.output);print(f'Backup created: {a.output}')
    elif a.cmd=='verify':verify_backup(a.archive);print('BACKUP_VERIFICATION_PASSED')
    else:restore_backup(a.archive,a.destination,a.force,a.postgres_url);print(f'Restored to: {a.destination}')

if __name__=='__main__':main()
