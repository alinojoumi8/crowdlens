"""Run the real platform loops against a controlled SQLite/OASIS boundary."""
import ast
import asyncio
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize('platform', ['twitter', 'reddit'])
@pytest.mark.parametrize('manual_succeeds', [True, False])
def test_worker_logs_only_executed_actions_with_phase_origins(tmp_path, monkeypatch, platform, manual_succeeds):
    scripts = Path(__file__).resolve().parents[1] / 'scripts'
    monkeypatch.syspath_prepend(str(scripts))
    from action_logger import PlatformActionLogger
    from app.services.simulation_activity import summarize_activity
    (tmp_path / f'{platform}_profiles.{"csv" if platform == "twitter" else "json"}').write_text('fixture')
    # Workers key actions by agent; the controlled agent is hashable.
    class Agent:
        name = 'Maya'
    agent = Agent()
    graph = SimpleNamespace(get_agent=lambda _: agent, get_agents=lambda: [(0, agent)])
    class Manual:
        def __init__(self, action_type, action_args):
            self.action_args = action_args
    class ModelAction:
        pass
    class Environment:
        agent_graph = graph
        async def reset(self):
            with sqlite3.connect(db_path) as db:
                db.execute('CREATE TABLE trace(user_id INTEGER, action TEXT, info TEXT)')
        async def step(self, actions):
            with sqlite3.connect(db_path) as db:
                for action in actions.values():
                    for item in action if isinstance(action, list) else [action]:
                        db.execute('INSERT INTO trace VALUES(0, ?, ?)', ('login', '{}'))
                        if isinstance(item, Manual) and not manual_succeeds:
                            continue
                        rowid = db.execute('SELECT COUNT(*) FROM trace').fetchone()[0] + 1
                        content = item.action_args['content'] if isinstance(item, Manual) else 'Actual model response'
                        db.execute('INSERT INTO trace VALUES(0, ?, ?)',
                            ('create_post', json.dumps({'content': content, 'post_id': rowid})))
    db_path = str(tmp_path / f'{platform}_simulation.db')
    database_bindings = []
    async def generate(**kwargs):
        return graph
    tree = ast.parse((scripts / 'run_parallel_simulation.py').read_text())
    selected = [node for node in tree.body if getattr(node, 'name', '') in
        {'PlatformSimulation', 'fetch_new_actions_from_db', f'run_{platform}_simulation'}]
    namespace = dict(os=os, json=json, sqlite3=sqlite3, datetime=datetime,
        Dict=dict, Any=object, List=list, Tuple=tuple, Optional=__import__('typing').Optional,
        PlatformActionLogger=PlatformActionLogger, SimulationLogManager=object,
        EconomyTickCoordinator=object, FILTERED_ACTIONS={'login'}, ACTION_TYPE_MAP={'create_post': 'CREATE_POST'},
        _enrich_action_context=lambda *args: None, create_model=lambda *args, **kw: None,
        generate_twitter_agent_graph=generate, generate_reddit_agent_graph=generate,
        bind_agent_database=lambda graph, path: database_bindings.append((graph, path)),
        TWITTER_ACTIONS=[], REDDIT_ACTIONS=[], get_agent_names_from_config=lambda _: {0: 'Maya'},
        oasis=SimpleNamespace(make=lambda **kw: Environment(),
            DefaultPlatformType=SimpleNamespace(TWITTER='twitter', REDDIT='reddit')),
        ManualAction=Manual, LLMAction=ModelAction, ActionType=SimpleNamespace(CREATE_POST='CREATE_POST'),
        _shutdown_event=None, resolve_simulation_start_hour=lambda _: 0,
        due_scheduled_events=lambda *args: [{'poster_agent_id': 0, 'content': 'Scheduled input', 'title': 'Notice'}],
        get_active_agents_for_round=lambda *args: [(0, agent)],
        inject_agent_forecast_memory=lambda *args: None,
        record_actions_to_short_memory=lambda *args: None, update_memory_summaries=lambda *args: None)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(scripts / 'run_parallel_simulation.py'), 'exec'), namespace)
    logger = PlatformActionLogger(platform, str(tmp_path))
    config = {'time_config': {'total_simulation_hours': 2, 'minutes_per_round': 60},
        'event_config': {'initial_posts': [{'poster_agent_id': 0, 'content': 'Initial input'}]}}
    asyncio.run(namespace[f'run_{platform}_simulation'](config, str(tmp_path), logger, max_rounds=1))
    assert database_bindings == [(graph, db_path)]
    rows = [json.loads(line) for line in (tmp_path / platform / 'actions.jsonl').read_text().splitlines()]
    actions = [row for row in rows if 'agent_id' in row]
    posts = [row for row in actions if row['action_type'] == 'CREATE_POST']
    assert [row['origin'] for row in posts] == (['initial_post', 'scheduled_event', 'model_action'] if manual_succeeds else ['model_action'])
    assert [row['trace_id'] for row in posts] == ([2, 4, 6] if manual_succeeds else [4])
    assert [row['round'] for row in posts] == ([0, 1, 1] if manual_succeeds else [1])
    assert summarize_activity(actions)['model_actions'] == 1
    start = next(row for row in rows if row.get('event_type') == 'simulation_start')
    assert start['total_rounds'] == 1
