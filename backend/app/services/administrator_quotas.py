"""Administrator-owned shared admission. All mutations use the workflow transaction.

Zero is a closed limit, never unlimited. Byte accounting is a conservative,
cumulative write allowance (overwrites and deleted files do not refund it).
Estimates and unresolved reservations are not provider billing.
"""
from contextvars import ContextVar
import json
import re
import uuid

from .workflow_spend import price_terms, estimated_micro_usd

LIMITS = {'requests', 'daily_requests', 'estimated_micro_usd', 'daily_estimated_micro_usd',
          'operations', 'daily_operations', 'storage_write_bytes', 'active_work'}
_OPERATION = ContextVar('quota_operation', default=None)


def halt(reason):
    from .workflow_execution import WorkflowHalt
    raise WorkflowHalt('quota_' + reason)


def initialize(db, *, required=False):
    db.execute('CREATE TABLE IF NOT EXISTS quota_settings (id INTEGER PRIMARY KEY, required INTEGER NOT NULL)')
    db.execute('INSERT OR IGNORE INTO quota_settings VALUES(1,0)')
    if required:
        db.execute('UPDATE quota_settings SET required=1 WHERE id=1')
    db.execute('CREATE TABLE IF NOT EXISTS quota_policies (scope TEXT PRIMARY KEY, payload TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS quota_audit (at REAL, actor TEXT, scope TEXT, payload TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS quota_attempts ('
               'request_id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, at REAL NOT NULL, '
               'estimated INTEGER NOT NULL, reserved INTEGER NOT NULL, pricing TEXT NOT NULL, finished INTEGER NOT NULL)')
    db.execute('CREATE INDEX IF NOT EXISTS quota_attempt_owner ON quota_attempts(workspace_id,at)')
    db.execute('CREATE TABLE IF NOT EXISTS quota_operations ('
               'id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, at REAL NOT NULL, active INTEGER NOT NULL)')
    db.execute('CREATE INDEX IF NOT EXISTS quota_operation_owner ON quota_operations(workspace_id,at)')
    db.execute('CREATE TABLE IF NOT EXISTS quota_storage_usage (workspace_id TEXT PRIMARY KEY, written INTEGER NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS quota_reconciliations (id TEXT PRIMARY KEY, at REAL, actor TEXT, payload TEXT)')


def managed(db):
    return bool(db.execute('SELECT required FROM quota_settings WHERE id=1').fetchone()[0])


def policies(db, workspace_id, *, admission=True):
    if not managed(db):
        return None
    if not workspace_id:
        halt('workspace_required')
    result = []
    for scope in ('global', workspace_id):
        row = db.execute('SELECT payload FROM quota_policies WHERE scope=?', (scope,)).fetchone()
        if not row:
            halt('not_configured')
        policy = json.loads(row[0])
        if admission and not policy['admission_open']:
            halt('admission_closed')
        result.append((scope, policy))
    return result


def update_policy(db, scope, payload, actor, now, *, identity=None):
    if scope != 'global' and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,199}', scope):
        raise ValueError('invalid_quota_account')
    expected = {'admission_open', 'limits'} | ({'pricing'} if scope == 'global' else set())
    if (not isinstance(payload, dict) or set(payload) != expected
            or type(payload['admission_open']) is not bool or not isinstance(payload['limits'], dict)
            or set(payload['limits']) != LIMITS
            or any(type(v) is not int or not 0 <= v <= 1_000_000_000_000 for v in payload['limits'].values())):
        raise ValueError('invalid_quota_policy')
    policy = json.loads(json.dumps(payload))
    if scope == 'global':
        if not identity:
            raise ValueError('quota_provider_identity_required')
        # Parsing also rejects unexpected pricing keys, NaN, floats and negative amounts.
        pricing = policy.pop('pricing')
        if not isinstance(pricing, dict) or 'budget_usd' in pricing:
            raise ValueError('invalid_quota_pricing')
        terms = price_terms({**pricing, 'budget_usd': '1000000'})
        policy['pricing'] = terms
        from .workflow_execution import endpoint_identity
        policy['identity'] = dict(provider=identity['provider'], model=identity['model'],
                                  endpoint_identity=endpoint_identity(identity['base_url']))
    db.execute('INSERT INTO quota_policies VALUES(?,?) ON CONFLICT(scope) DO UPDATE SET payload=excluded.payload',
               (scope, json.dumps(policy)))
    db.execute('INSERT INTO quota_audit VALUES(?,?,?,?)', (now, actor, scope, json.dumps(policy)))
    return policy


def public_policy(policy):
    """Keep GET policy documents round-trippable through PUT."""
    if policy is None:
        return None
    value = dict(admission_open=policy['admission_open'], limits=policy['limits'])
    if 'pricing' in policy:
        p = policy['pricing']
        def usd(n):
            return f'{n // 1000000}.{n % 1000000:06d}'
        value['pricing'] = dict(currency='USD', reserve_usd=usd(p['reserve_micro_usd']),
            input_usd_per_million=usd(p['input_rate_micro_usd']),
            output_usd_per_million=usd(p['output_rate_micro_usd']), price_reference=p['price_reference'])
    return value


def usage(db, scope, now):
    where, args = ('', ()) if scope == 'global' else (' WHERE workspace_id=?', (scope,))
    day = int(now // 86400) * 86400
    row = db.execute('SELECT COUNT(*),COALESCE(SUM(at>=?),0),COALESCE(SUM(estimated+reserved),0),'
        'COALESCE(SUM(CASE WHEN at>=? THEN estimated ELSE 0 END)+SUM(reserved),0),'
        'COALESCE(SUM(reserved),0) FROM quota_attempts' + where, (day, day, *args)).fetchone()
    ops = db.execute('SELECT COUNT(*),COALESCE(SUM(at>=?),0),'
        'COALESCE(SUM(CASE WHEN id!=? THEN active ELSE 0 END),0) FROM quota_operations' + where,
        (day, _OPERATION.get() or '', *args)).fetchone()
    written = db.execute('SELECT COALESCE(SUM(written),0) FROM quota_storage_usage' + where, args).fetchone()[0]
    # Task ownership/recovery owns lifecycle; a process restart never frees a pending task here.
    tasks = 0
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='tasks'").fetchone():
        for item in db.execute('SELECT payload_json FROM tasks'):
            task = json.loads(item[0])
            if task.get('status') in {'pending', 'processing'} and (scope == 'global' or task.get('workspace_id') == scope):
                tasks += 1
    return dict(requests=row[0], daily_requests=row[1], estimated_micro_usd=row[2],
        daily_estimated_micro_usd=row[3], reserved_micro_usd=row[4], operations=ops[0],
        daily_operations=ops[1], storage_write_bytes=written, active_work=ops[2] + tasks)


def check(db, workspace_id, now, additions, *, admission=True):
    configured = policies(db, workspace_id, admission=admission)
    if configured:
        for scope, policy in configured:
            used = usage(db, scope, now)
            for metric, amount in additions.items():
                if used[metric] + amount > policy['limits'][metric]:
                    halt(metric + '_limit')
    return configured


def authorization_spend(db, workspace_id, now, identity, spend):
    configured = check(db, workspace_id, now, {})
    if not configured:
        return spend
    global_policy = configured[0][1]
    from .workflow_execution import endpoint_identity
    if global_policy['identity'] != dict(provider=identity['provider'], model=identity['model'],
            endpoint_identity=endpoint_identity(identity['base_url'])):
        halt('provider_changed')
    pricing = global_policy['pricing']
    ceiling = min(p['limits']['estimated_micro_usd'] for _, p in configured)
    if ceiling < pricing['reserve_micro_usd']:
        halt('estimated_micro_usd_limit')
    def usd(n):
        return f'{n // 1000000}.{n % 1000000:06d}'
    # Client pricing never participates in shared accounting. A client can still
    # opt for a smaller workflow budget; omission uses the administrator ceiling.
    return dict(currency='USD', budget_usd=spend.get('budget_usd', usd(ceiling)) if isinstance(spend, dict) else usd(ceiling),
        reserve_usd=usd(pricing['reserve_micro_usd']), input_usd_per_million=usd(pricing['input_rate_micro_usd']),
        output_usd_per_million=usd(pricing['output_rate_micro_usd']), price_reference=pricing['price_reference'])


def admit(db, workspace_id, now, ticket, provider, model, endpoint):
    configured = policies(db, workspace_id)
    if not configured:
        return
    global_policy = configured[0][1]
    if global_policy['identity'] != dict(provider=provider, model=model, endpoint_identity=endpoint):
        halt('provider_changed')
    pricing = global_policy['pricing']
    reserve = pricing['reserve_micro_usd']
    check(db, workspace_id, now, dict(requests=1, daily_requests=1,
        estimated_micro_usd=reserve, daily_estimated_micro_usd=reserve, storage_write_bytes=1))
    db.execute('INSERT INTO quota_attempts VALUES(?,?,?,?,?,?,0)',
        (ticket['request_id'], workspace_id, now, 0, reserve, json.dumps(pricing)))


def finish(db, ticket, usage_value):
    row = db.execute('SELECT pricing,finished,reserved FROM quota_attempts WHERE request_id=?', (ticket['request_id'],)).fetchone()
    if not row or row[1]:
        return
    estimate = estimated_micro_usd(usage_value, json.loads(row[0]))
    if estimate is None:
        db.execute('UPDATE quota_attempts SET finished=1 WHERE request_id=?', (ticket['request_id'],))
    else:
        db.execute('UPDATE quota_attempts SET estimated=?,reserved=0,finished=1 WHERE request_id=?',
                   (estimate, ticket['request_id']))
        if estimate > row[2]:
            policy = json.loads(db.execute("SELECT payload FROM quota_policies WHERE scope='global'").fetchone()[0])
            policy['admission_open'] = False
            db.execute("UPDATE quota_policies SET payload=? WHERE scope='global'", (json.dumps(policy),))
            db.execute('INSERT INTO quota_audit VALUES(?,?,?,?)',
                (ticket['admitted_at'], 'system:reservation_exceeded', 'global', json.dumps(policy)))


def begin_operation(db, workspace_id, now, *, admission=True, active=True):
    additions = dict(operations=1, daily_operations=1)
    if active:
        additions['active_work'] = 1
    if admission:
        additions['storage_write_bytes'] = 1
    if not check(db, workspace_id, now, additions, admission=admission):
        return None
    identifier = 'op_' + uuid.uuid4().hex
    db.execute('INSERT INTO quota_operations VALUES(?,?,?,?)', (identifier, workspace_id, now, int(active)))
    return identifier


def charge_storage(db, workspace_id, now, size):
    if type(size) is not int or size < 0:
        raise ValueError('invalid_storage_size')
    if check(db, workspace_id, now, dict(storage_write_bytes=size), admission=False):
        db.execute('INSERT INTO quota_storage_usage VALUES(?,?) ON CONFLICT(workspace_id) '
                   'DO UPDATE SET written=written+excluded.written', (workspace_id, size))


def snapshot(db, workspace_id, now):
    configured = policies(db, workspace_id, admission=False)
    if not configured:
        return None
    reason = None
    from .workflow_execution import WorkflowHalt
    reserve = configured[0][1]['pricing']['reserve_micro_usd']
    try:
        check(db, workspace_id, now, dict(requests=1, daily_requests=1,
            estimated_micro_usd=reserve, daily_estimated_micro_usd=reserve, storage_write_bytes=1))
    except WorkflowHalt as exc:
        reason = exc.reason
    return dict(managed=True, admission_open=reason is None, reason=reason,
        workspace=dict(limits=configured[1][1]['limits'], usage=usage(db, workspace_id, now)),
        global_admission_open=configured[0][1]['admission_open'],
        billing_amount=None, guarantee='shared_admission_estimates_not_provider_billing',
        pricing=configured[0][1]['pricing'])


def reconcile(db, payload, actor, now):
    fields = {'period_start', 'period_end', 'reported_micro_usd', 'reported_requests', 'reference'}
    if (not isinstance(payload, dict) or set(payload) != fields
            or any(type(payload[k]) is not int or not 0 <= payload[k] <= 1_000_000_000_000
                   for k in fields - {'reference'})
            or not payload['period_start'] < payload['period_end'] <= now + 1
            or not isinstance(payload['reference'], str) or not 1 <= len(payload['reference'].strip()) <= 500):
        raise ValueError('invalid_reconciliation_receipt')
    row = db.execute('SELECT COUNT(*),COALESCE(SUM(estimated),0),COALESCE(SUM(reserved),0) '
        'FROM quota_attempts WHERE at>=? AND at<?', (payload['period_start'], payload['period_end'])).fetchone()
    receipt = dict(payload, id='reconcile_' + uuid.uuid4().hex, recorded_at=now,
        admitted_requests=row[0], estimated_micro_usd=row[1], reserved_micro_usd=row[2],
        reported_minus_estimate_micro_usd=payload['reported_micro_usd'] - row[1],
        provenance='administrator_supplied_provider_statement_not_independently_verified')
    # A provider aggregate is not evidence that a particular unknown request
    # was free. Reconciliation never releases a reservation or resets counters.
    db.execute('INSERT INTO quota_reconciliations VALUES(?,?,?,?)', (receipt['id'], now, actor, json.dumps(receipt)))
    return receipt
