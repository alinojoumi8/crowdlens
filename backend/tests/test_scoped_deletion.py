"""Project deletion must be confined before touching metadata or disk."""
from pathlib import Path

from flask import Flask
import pytest

from app.api import graph_bp
import app.api.graph  # Register the routes without starting services.
from app.models.case import CaseManager
from app.models.project import ProjectManager
from app.storage.control_db import ControlDatabase


@pytest.fixture
def stores(tmp_path, monkeypatch):
    database = ControlDatabase(tmp_path / 'control.db')
    monkeypatch.setattr(ProjectManager, 'PROJECTS_DIR', str(tmp_path / 'projects'))
    monkeypatch.setattr(ProjectManager, '_repository', database)
    monkeypatch.setattr(CaseManager, 'CASES_DIR', str(tmp_path / 'cases'))
    monkeypatch.setattr(CaseManager, '_repository', database)
    app = Flask(__name__)
    app.register_blueprint(graph_bp, url_prefix='/api/graph')
    return database, app.test_client()


@pytest.mark.parametrize('identifier', ['..', '.', '../other', 'ABSOLUTE', 'a/b', 'a\\b', '', ' x', 'a\x00b'])
def test_invalid_deletion_never_touches_repository_or_unrelated_files(stores, tmp_path, identifier):
    database, _ = stores
    if identifier == 'ABSOLUTE':
        identifier = str(tmp_path / 'other-case')
    Path(ProjectManager.PROJECTS_DIR).mkdir()
    stored_id = identifier or 'proj_retained'
    database.put_project({'project_id': stored_id, 'name': 'Synthetic invalid legacy record'})
    marker = tmp_path / 'unrelated.txt'
    marker.write_text('Preserve this source')
    with pytest.raises(ValueError):
        ProjectManager.delete_project(identifier)
    assert database.get_project(stored_id) is not None
    assert marker.read_text() == 'Preserve this source'


def test_http_traversal_rejected_before_database_change(stores, tmp_path):
    database, client = stores
    Path(ProjectManager.PROJECTS_DIR).mkdir()
    database.put_project({'project_id': '..'})
    response = client.delete('/api/graph/project/%2E%2E')
    assert response.status_code == 400 and not response.json['success']
    assert 'traceback' not in response.json
    assert database.get_project('..') is not None
    assert tmp_path.is_dir()


def test_symlink_project_rejected_before_metadata_deletion(stores, tmp_path):
    database, client = stores
    projects = Path(ProjectManager.PROJECTS_DIR)
    projects.mkdir()
    target = tmp_path / 'other-case'
    target.mkdir()
    (target / 'source.txt').write_text('Unrelated source')
    (projects / 'proj_link').symlink_to(target, target_is_directory=True)
    database.put_project({'project_id': 'proj_link'})
    assert client.delete('/api/graph/project/proj_link').status_code == 400
    assert database.get_project('proj_link') is not None
    assert (target / 'source.txt').read_text() == 'Unrelated source'


def test_filesystem_failure_keeps_metadata_and_reports_failure(stores, tmp_path, monkeypatch):
    database, client = stores
    project = ProjectManager.create_project('Selected project')
    def fail(path):
        raise OSError('synthetic filesystem failure')
    monkeypatch.setattr('app.models.project.shutil.rmtree', fail)
    response = client.delete('/api/graph/project/' + project.project_id)
    assert response.status_code == 503 and not response.json['success']
    assert 'traceback' not in response.json
    assert database.get_project(project.project_id) is not None


def test_only_selected_project_is_deleted_retaining_case_history_and_other_artifacts(stores, tmp_path):
    database, client = stores
    first = ProjectManager.create_project('Selected project')
    other = ProjectManager.create_project('Unrelated project')
    cases = []
    for project in (first, other):
        source = Path(ProjectManager.PROJECTS_DIR) / project.project_id / 'files' / 'source.txt'
        source.write_text(project.name)
        case = CaseManager.create_case(project.name)
        CaseManager.create_version(case.case_id, project.project_id, graph_id='graph_' + project.project_id,
            documents=[{'filename': 'source.txt', 'path': str(source), 'text': project.name}])
        cases.append(case.case_id)
    reports = tmp_path / 'reports'; reports.mkdir()
    (reports / 'saved-report.md').write_text('Retained report')
    simulation = tmp_path / 'simulation'; simulation.mkdir()
    (simulation / 'actions.jsonl').write_text('Retained action log')
    retained = {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file() and
        (p.is_relative_to(reports) or p.is_relative_to(simulation) or other.project_id in p.parts)}
    case_before = {key: database.get_case(key) for key in cases}
    other_before = database.get_project(other.project_id)
    assert client.delete('/api/graph/project/' + first.project_id).status_code == 200
    assert database.get_project(first.project_id) is None
    assert not (Path(ProjectManager.PROJECTS_DIR) / first.project_id).exists()
    assert database.get_project(other.project_id) == other_before
    assert {key: database.get_case(key) for key in cases} == case_before
    assert all(path.read_bytes() == content for path, content in retained.items())
    assert client.delete('/api/graph/project/' + first.project_id).status_code == 404
