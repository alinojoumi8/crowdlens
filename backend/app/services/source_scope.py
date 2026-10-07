"""Resolve the original case version; never substitute the latest version."""
from .claim_ledger import SCOPE_KEYS


def source_scope(parent_snapshot, simulation_config):
    candidates = [parent_snapshot.get('source_grounding') or {}, simulation_config or {},
                  {'graph_id': parent_snapshot.get('graph_id')}]
    scope = {}
    for key in SCOPE_KEYS:
        values = [row[key] for row in candidates if row.get(key)]
        if not values or any(not isinstance(value, str) or value != values[0] for value in values):
            raise ValueError('scope_mismatch')
        scope[key] = values[0]
    return scope


def resolve_source_scope(snapshot, config, *, project_loader=None, case_loader=None):
    try:
        return source_scope(snapshot, config)
    except ValueError:
        pass
    if project_loader is None:
        from ..models.project import ProjectManager
        project_loader = ProjectManager.get_project
    if case_loader is None:
        from ..models.case import CaseManager
        case_loader = CaseManager.get_case
    config = config or {}
    project_id, graph_id = config.get('project_id'), config.get('graph_id')
    if not isinstance(project_id, str) or not project_id or not isinstance(graph_id, str) or not graph_id:
        raise ValueError('scope_mismatch')
    project = project_loader(project_id)
    case = case_loader(project.case_id) if project and project.case_id else None
    matches = [version for version in case.versions
               if version.project_id == project_id and version.graph_id == graph_id] if case else []
    if len(matches) != 1:
        raise ValueError('scope_mismatch')
    inferred = {'case_id': case.case_id, 'case_version_id': matches[0].version_id, 'graph_id': graph_id}
    for row in (snapshot.get('source_grounding') or {}, config):
        if any(row.get(key) and row[key] != value for key, value in inferred.items()):
            raise ValueError('scope_mismatch')
    return source_scope(snapshot, {**config, **inferred})
