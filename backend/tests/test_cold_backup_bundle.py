import copy
import json
import sqlite3
from pathlib import Path

import pytest
from scripts.cold_backup_bundle import create_bundle,inventory,restore_artifacts,verify_bundle


@pytest.fixture
def packet(tmp_path):
    root=tmp_path/'data';root.mkdir()
    with sqlite3.connect(root/'control.db') as db:
        db.execute('create table preserved(value text)');db.execute("insert into preserved values ('original')")
    reviews=root/'reports'/'.evidence-proposals';reviews.mkdir(parents=True)
    with sqlite3.connect(reviews/'.human-reviews.sqlite3') as db:
        db.execute('create table labels(value text)');db.execute("insert into labels values ('synthetic pending')")
    (root/'report.md').write_text('Original immutable report')
    dump=tmp_path/'fixture.dump';dump.write_bytes(b'synthetic dump; actual Neo4j tested in separate rehearsal')
    options=dict(revision='a'*40,app_image='sha256:'+'b'*64,neo4j_image='sha256:'+'c'*64,
                 quiescence=dict(application_writers_stopped=True,neo4j_stopped_during_dump=True,
                    exclusive_graph_ownership=True,observed_at='2026-10-10T00:00:00Z',note='Synthetic fixture writers exited.'))
    return root,dump,options


def test_bundle_restores_all_hidden_files_and_integrity_without_overwrite(packet,tmp_path):
    root,dump,options=packet;before=inventory(root)
    manifest=create_bundle({'uploads':root},dump,tmp_path/'bundle',**options)
    assert len(manifest['sqlite_integrity_checked'])==2
    assert manifest['source_metadata']['uploads']['report.md']['uid']==(root/'report.md').stat().st_uid
    restore_artifacts(tmp_path/'bundle',tmp_path/'restored')
    assert inventory(tmp_path/'restored/stores/uploads')==before==inventory(root)
    with pytest.raises(FileExistsError):restore_artifacts(tmp_path/'bundle',tmp_path/'restored')
    with pytest.raises(FileExistsError):create_bundle({'uploads':root},dump,tmp_path/'bundle',**options)


def test_corrupt_dump_or_artifact_is_rejected_before_restore(packet,tmp_path):
    root,dump,options=packet
    create_bundle({'uploads':root},dump,tmp_path/'bundle',**options)
    (tmp_path/'bundle/neo4j.dump').write_text('corrupted')
    with pytest.raises(ValueError,match='bundle_hash_mismatch'):restore_artifacts(tmp_path/'bundle',tmp_path/'restored')
    assert not (tmp_path/'restored').exists()


def test_unsafe_or_live_inputs_are_rejected(packet,tmp_path):
    root,dump,options=packet
    bad=copy.deepcopy(options);bad['quiescence']['exclusive_graph_ownership']=False
    with pytest.raises(ValueError,match='missing_quiescence'):create_bundle({'uploads':root},dump,tmp_path/'bundle',**bad)
    bad=copy.deepcopy(options);bad['quiescence']['observed_at']='REPLACE_WITH_ACTUAL_UTC_TIME'
    with pytest.raises(ValueError,match='quiescence_time_required'):create_bundle({'uploads':root},dump,tmp_path/'bundle',**bad)
    with pytest.raises(ValueError,match='overlapping'):create_bundle({'uploads':root},dump,root/'bundle',**options)
    (root/'linked').symlink_to(dump)
    with pytest.raises(ValueError,match='symlinks'):create_bundle({'uploads':root},dump,tmp_path/'bundle',**options)


def test_failed_copy_never_looks_like_complete_backup(packet,tmp_path,monkeypatch):
    from scripts import cold_backup_bundle as module
    root,dump,options=packet;before=inventory(root)
    def no_space(*a,**k):raise OSError('no space in synthetic destination')
    monkeypatch.setattr(module.shutil,'copytree',no_space)
    with pytest.raises(OSError):create_bundle({'uploads':root},dump,tmp_path/'bundle',**options)
    assert not (tmp_path/'bundle/manifest.json').exists()
    assert inventory(root)==before


def test_concurrent_source_change_is_detected(packet,tmp_path,monkeypatch):
    from scripts import cold_backup_bundle as module
    root,dump,options=packet;real=module.shutil.copytree
    def changed(*a,**k):
        out=real(*a,**k);(root/'report.md').write_text('new content during copy');return out
    monkeypatch.setattr(module.shutil,'copytree',changed)
    with pytest.raises(ValueError,match='source_changed'):create_bundle({'uploads':root},dump,tmp_path/'bundle',**options)
    assert not (tmp_path/'bundle/manifest.json').exists()
