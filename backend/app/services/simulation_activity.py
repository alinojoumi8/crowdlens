"""Recorded activity accounting. Initial/event inputs are not model responses."""
import json
from pathlib import Path

ORIGINS = {'initial_post', 'scheduled_event', 'model_action', 'unknown'}


def unique_actions(rows):
    result, seen = [], set()
    for row in rows:
        if not isinstance(row, dict) or row.get('agent_id') is None or not row.get('action_type'):
            continue
        args = row.get('action_args') if isinstance(row.get('action_args'), dict) else {}
        platform = row.get('platform', '')
        if row['action_type'] == 'CREATE_POST' and args.get('post_id') is not None:
            key = (platform, 'post', str(args['post_id']))
        elif row.get('trace_id') is not None:
            key = (platform, 'trace', str(row['trace_id']))
        else:
            # A timestamp is part of the legacy identity: repeated actions in
            # different rounds are not duplicates just because text matches.
            key = (platform, row.get('round_num', row.get('round')), row.get('timestamp'),
                   row['agent_id'], row['action_type'], json.dumps(args, sort_keys=True))
        if key in seen:
            continue
        seen.add(key)
        origin = row.get('origin', 'unknown')
        result.append({**row, 'origin': origin if origin in ORIGINS else 'unknown'})
    return result


def read_activity(simulation_dir):
    rows = []
    for platform in ('twitter', 'reddit'):
        path = Path(simulation_dir) / platform / 'actions.jsonl'
        if not path.exists():
            continue
        with path.open(encoding='utf-8') as stream:
            for line in stream:
                try:
                    row = json.loads(line)
                except (ValueError, TypeError):
                    continue
                if isinstance(row, dict) and row.get('agent_id') is not None and row.get('action_type'):
                    rows.append({**row, 'platform': platform})
    return rows


def summarize_activity(rows):
    valid = [r for r in rows if isinstance(r, dict) and r.get('agent_id') is not None and r.get('action_type')]
    unique = unique_actions(valid)
    posts = [r for r in unique if r['action_type'] == 'CREATE_POST' and r.get('success', True)]
    model = [r for r in unique if r['origin'] == 'model_action']
    successful = [r for r in model if r.get('success', True) and r['action_type'] != 'DO_NOTHING']
    return {'model_written_actions': sum(r['action_type'] in ('CREATE_POST', 'CREATE_COMMENT') for r in successful),
            'model_reactions': sum(r['action_type'] not in ('CREATE_POST', 'CREATE_COMMENT') for r in successful),
            'model_noops': sum(r['action_type'] == 'DO_NOTHING' for r in model),
            'model_failed_actions': sum(not r.get('success', True) for r in model),
            'logged_entries': len(valid), 'unique_posts': len(posts),
            'model_actions': sum(r['origin'] == 'model_action' for r in unique),
            'initial_posts': sum(r['origin'] == 'initial_post' for r in posts),
            'scheduled_posts': sum(r['origin'] == 'scheduled_event' for r in posts),
            'scheduled_events': sum(r['action_type'] == 'SCHEDULED_EVENT' for r in unique),
            'unknown_origin_actions': sum(r['origin'] == 'unknown' for r in unique)}


def forecast_actions(rows):
    """Exclude input posts, event metadata, no-ops, failures and duplicate rows.

    Legacy unknown-origin actions retain compatibility, but are labelled unknown
    in accounting/provenance and never labelled model responses.
    """
    return [r for r in unique_actions(rows)
            if r['origin'] in ('model_action', 'unknown') and r.get('success', True)
            and type(r.get('agent_id')) is int and r['agent_id'] >= 0
            and type(r.get('round_num', r.get('round', 1))) in (int, float)
            and r.get('round_num', r.get('round', 1)) > 0
            and r['action_type'] not in ('SCHEDULED_EVENT', 'DO_NOTHING')]
