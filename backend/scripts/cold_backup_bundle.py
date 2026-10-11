"""Assemble and verify a quiesced artifact/SQLite + offline Neo4j dump bundle.

This tool does not stop services or prove quiescence. It requires a recorded
operator attestation, detects changes during copying, and never overwrites a
backup or restore target. Store bundles privately: they contain source data.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import sqlite3
import tempfile
import uuid


def sha256_file(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()


def source_metadata(root):
    result={}
    for path in [root,*root.rglob('*')]:
        stat=path.lstat()
        result[path.relative_to(root).as_posix()]={'uid':stat.st_uid,'gid':stat.st_gid,'mode':stat.st_mode & 0o7777}
    return result


def inventory(root):
    result = {}
    for path in sorted(Path(root).rglob('*')):
        if path.is_symlink():
            raise ValueError('symlinks_are_not_supported')
        if path.is_file():
            result[path.relative_to(root).as_posix()] = sha256_file(path)
        elif not path.is_dir():
            raise ValueError('special_files_are_not_supported')
    return result


def sqlite_integrity(root):
    checked = []
    for path in Path(root).rglob('*'):
        if not path.is_file() or path.suffix not in {'.db', '.sqlite', '.sqlite3'}:
            continue
        with path.open('rb') as handle:
            if handle.read(16) != b'SQLite format 3\x00':
                raise ValueError('sqlite_header_invalid:' + str(path.relative_to(root)))
        # Opening a WAL database can modify shared-memory files. Inspect a
        # disposable copy, never the preserved backup or its source.
        with tempfile.TemporaryDirectory(prefix='crowdlens-sqlite-check-') as tmp:
            target = Path(tmp)/path.name
            shutil.copy2(path, target)
            for suffix in ('-wal','-shm','-journal'):
                sidecar = Path(str(path)+suffix)
                if sidecar.exists(): shutil.copy2(sidecar, Path(str(target)+suffix))
            with sqlite3.connect(target) as db:
                if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                    raise ValueError('sqlite_integrity_failed')
        checked.append(path.relative_to(root).as_posix())
    return checked


def create_bundle(roots, neo4j_dump, destination, *, revision, app_image, neo4j_image, quiescence):
    destination = Path(destination).absolute()
    for field in ('application_writers_stopped','neo4j_stopped_during_dump','exclusive_graph_ownership'):
        if quiescence.get(field) is not True:
            raise ValueError('missing_quiescence_attestation:' + field)
    if not quiescence.get('observed_at') or not quiescence.get('note'):
        raise ValueError('quiescence_receipt_required')
    try:
        if datetime.fromisoformat(quiescence['observed_at']).tzinfo is None:
            raise ValueError('timezone_required')
    except (ValueError, TypeError) as exc:
        raise ValueError('actual_timezone_bearing_quiescence_time_required') from exc
    if not re.fullmatch('[0-9a-f]{40}', revision) or any(not re.fullmatch('sha256:[0-9a-f]{64}', v) for v in (app_image,neo4j_image)):
        raise ValueError('immutable_revision_and_image_ids_required')
    roots = {name:Path(path).absolute() for name,path in roots.items()}
    if not roots or any(not re.fullmatch('[a-z][a-z0-9_-]*', name) for name in roots):
        raise ValueError('invalid_store_names')
    for root in roots.values():
        if root.is_symlink() or not root.is_dir() or destination.resolve().is_relative_to(root.resolve()):
            raise ValueError('invalid_or_overlapping_source_destination')
    dump = Path(neo4j_dump)
    if dump.is_symlink() or not dump.is_file(): raise ValueError('regular_neo4j_dump_required')
    before = {name:inventory(root) for name,root in roots.items()}
    metadata = {name:source_metadata(root) for name,root in roots.items()}
    dump_digest = sha256_file(dump)
    destination.mkdir(mode=0o700)  # existing destinations are never reused
    (destination/'stores').mkdir()
    for name,root in roots.items():
        shutil.copytree(root,destination/'stores'/name)
        if inventory(root) != before[name] or inventory(destination/'stores'/name) != before[name]:
            raise ValueError('source_changed_during_copy')
    shutil.copy2(dump,destination/'neo4j.dump')
    if sha256_file(destination/'neo4j.dump') != dump_digest or sha256_file(dump) != dump_digest:
        raise ValueError('dump_changed_during_copy')
    if any(inventory(root) != before[name] or source_metadata(root) != metadata[name] for name,root in roots.items()):
        raise ValueError('source_changed_during_copy')
    checks=sqlite_integrity(destination/'stores')
    manifest=dict(schema_version=1,bundle_id=str(uuid.uuid4()),created_at=datetime.now(timezone.utc).isoformat(),
                  revision=revision,app_image=app_image,neo4j_image=neo4j_image,
                  quiescence=quiescence,quiescence_evidence='operator_attested; not independently established by this tool',
                  source_metadata=metadata,
                  original_roots={name:str(root) for name,root in roots.items()},
                  sqlite_integrity_checked=checks,files=inventory(destination),
                  limitations=['Cold backup only; no online atomicity or power-loss guarantee.',
                               'Active task recovery requires the original absolute resource roots.',
                               'Restore never authorizes new generation or resumes paid work.'])
    with (destination/'manifest.json').open('x') as handle:
        json.dump(manifest,handle,indent=2);handle.write('\n')
    verify_bundle(destination)
    return manifest


def verify_bundle(bundle):
    bundle=Path(bundle)
    if bundle.is_symlink() or (bundle/'manifest.json').is_symlink():raise ValueError('symlinks_are_not_supported')
    manifest=json.loads((bundle/'manifest.json').read_text())
    if manifest.get('schema_version') != 1:raise ValueError('unsupported_bundle_schema')
    actual=inventory(bundle);actual.pop('manifest.json',None)
    if actual != manifest['files']:raise ValueError('bundle_hash_mismatch')
    sqlite_integrity(bundle/'stores')
    return manifest


def restore_artifacts(bundle, destination):
    bundle=Path(bundle).resolve();destination=Path(destination).absolute()
    manifest=verify_bundle(bundle)
    if destination.resolve().is_relative_to(bundle):raise ValueError('restore_inside_bundle')
    destination.mkdir(mode=0o700)
    shutil.copytree(bundle/'stores',destination/'stores')
    shutil.copy2(bundle/'neo4j.dump',destination/'neo4j.dump')
    if inventory(destination) != manifest['files']:raise ValueError('restore_hash_mismatch')
    sqlite_integrity(destination/'stores')
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='action',required=True)
    create=sub.add_parser('create')
    create.add_argument('--root',action='append',required=True,help='Store name=/absolute/directory; repeat for external report/database roots')
    for option in ('neo4j-dump','output','revision','app-image','neo4j-image','quiescence-receipt'):
        create.add_argument('--'+option,required=True)
    verify=sub.add_parser('verify');verify.add_argument('bundle')
    restore=sub.add_parser('restore-artifacts');restore.add_argument('bundle');restore.add_argument('--output',required=True)
    args=parser.parse_args()
    if args.action=='create':
        roots=dict(value.split('=',1) for value in args.root)
        if len(roots)!=len(args.root):parser.error('Store names must be unique')
        result=create_bundle(roots,args.neo4j_dump,args.output,revision=args.revision,app_image=args.app_image,
                             neo4j_image=args.neo4j_image,quiescence=json.loads(Path(args.quiescence_receipt).read_text()))
    elif args.action=='verify':result=verify_bundle(args.bundle)
    else:result=restore_artifacts(args.bundle,args.output)
    print(json.dumps({'bundle_id':result['bundle_id'],'verified_files':len(result['files']), 'sqlite_databases':len(result['sqlite_integrity_checked'])}))


if __name__=='__main__':main()
