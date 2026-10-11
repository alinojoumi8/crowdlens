"""Application status: liveness is separate from non-generation readiness."""
from pathlib import Path
from flask import current_app, jsonify

from ..config import Config
from ..utils.build_identity import runtime_identity
from ..services.jev_policy import decision_configuration
from ..services.readiness import disk_readiness, model_metadata
from . import status_bp


def storage_readiness(app):
    from ..services.report_agent import ReportManager
    paths = {'uploads': app.config.get('UPLOAD_FOLDER', Config.UPLOAD_FOLDER),
             'reports': ReportManager._get_reports_dir()}
    db_path = app.config.get('CONTROL_DB_PATH')
    if db_path:
        paths['saved_data'] = Path(db_path).parent
    return disk_readiness(paths, warning_bytes=app.config.get('DISK_WARNING_BYTES', 2 * 1024**3),
                          critical_bytes=app.config.get('DISK_CRITICAL_BYTES', 512 * 1024**2))


def readiness_state(neo4j, embedding, control, disk, llm):
    if not neo4j.get('healthy') or not control.get('healthy') or disk.get('state') in {'critical','unavailable'}:
        return 'unavailable'
    providers = [embedding, llm]
    if any(row.get('state') in {'unconfigured','missing_model','unavailable'} for row in providers):
        return 'unavailable'
    if any(row.get('state') == 'checking' for row in providers) or disk.get('state') == 'checking':
        return 'checking'
    if any(not row.get('healthy') for row in providers):
        return 'unverified'
    return 'warning' if disk.get('state') == 'warning' else 'ready'


@status_bp.route('/status', methods=['GET'])
def get_status():
    storage = current_app.extensions.get('neo4j_storage')
    control_db = current_app.extensions.get('control_db')
    control = control_db.health_status() if control_db else {'healthy':False,'error':'Control database not initialized'}
    control['migration'] = current_app.extensions.get('control_db_migration', {})
    control['runner_reconciliation'] = current_app.extensions.get('simulation_reconciliation', {'checked':0,'alive':0,'interrupted':0})
    llm = model_metadata(Config.LLM_DEFAULT_PROVIDER, Config.LLM_BASE_URL, Config.LLM_MODEL_NAME, Config.LLM_API_KEY)
    llm['base_url'] = Config.LLM_BASE_URL
    neo4j = storage.health_status() if storage else {'healthy':False,'error':'GraphStorage not initialized','uri':Config.NEO4J_URI}
    embedding = neo4j.get('embedding', {'healthy':False, 'state':'unavailable','error':'GraphStorage not initialized'})
    disk = storage_readiness(current_app)
    state = readiness_state(neo4j, embedding, control, disk, llm)
    data = dict(service='CrowdLens Backend', build=runtime_identity(), healthy=state in {'ready','warning'},
                readiness=state, llm=llm, decisions=decision_configuration(),
                neo4j={k:v for k,v in neo4j.items() if k != 'embedding'}, embedding=embedding,
                vector_search_usable=bool(neo4j.get('vector_search_usable')), control_db=control, disk=disk,
                inference_verified=False)
    response = jsonify(success=True,data=data)
    response.headers['Cache-Control'] = 'no-store'
    return response
