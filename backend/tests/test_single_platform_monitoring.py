"""Verify single-platform launch and CLI-to-monitor events without loading OASIS models."""
import argparse
import ast
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services.simulation_runner import RunnerStatus, SimulationRunner, SimulationRunState


@pytest.mark.parametrize('platform', ['twitter', 'reddit'])
def test_single_platform_launch_uses_the_observable_worker(tmp_path, monkeypatch, platform):
    sim_dir = tmp_path / 'sim_one'
    sim_dir.mkdir()
    (sim_dir / 'simulation_config.json').write_text(json.dumps({
        'time_config': {'total_simulation_hours': 2, 'minutes_per_round': 60},
    }))
    monkeypatch.setattr(SimulationRunner, 'RUN_STATE_DIR', str(tmp_path))
    for name in ('_run_states', '_processes', '_stdout_files', '_stderr_files', '_graph_memory_enabled'):
        monkeypatch.setattr(SimulationRunner, name, {})
    monkeypatch.setattr(SimulationRunner, '_repository', None)
    monkeypatch.setattr(SimulationRunner, '_monitor_simulation', lambda *args: None)
    commands = []
    def launch(command, **kwargs):
        commands.append(command)
        return SimpleNamespace(pid=12345)
    monkeypatch.setattr('app.services.simulation_runner.subprocess.Popen', launch)
    try:
        state = SimulationRunner.start_simulation('sim_one', platform=platform, memory_mode='off')
        assert Path(commands[0][1]).name == 'run_parallel_simulation.py'
        assert '--' + platform + '-only' in commands[0]
        assert state.twitter_running == (platform == 'twitter')
        assert state.reddit_running == (platform == 'reddit')
        assert state.total_rounds == 2
    finally:
        for handle in SimulationRunner._stdout_files.values():
            handle.close()


@pytest.mark.parametrize('platform', ['twitter', 'reddit'])
def test_single_platform_cli_emits_events_consumed_as_completed(tmp_path, monkeypatch, platform):
    # Execute the real CLI function with a controlled OASIS boundary, avoiding
    # module-level third-party model loading. The logger and monitor are real.
    scripts = Path(__file__).resolve().parents[1] / 'scripts'
    monkeypatch.syspath_prepend(str(scripts))
    from action_logger import SimulationLogManager
    tree = ast.parse((scripts / 'run_parallel_simulation.py').read_text())
    main = next(node for node in tree.body if isinstance(node, ast.AsyncFunctionDef) and node.name == 'main')
    config_path = tmp_path / 'simulation_config.json'
    config = {'time_config': {'total_simulation_hours': 2, 'minutes_per_round': 60}, 'agent_configs': []}
    config_path.write_text(json.dumps(config))
    async def controlled_worker(config, directory, logger, *args):
        assert logger.platform == platform
        for round_num in (1, 2):
            logger.log_round_start(round_num, round_num - 1)
            logger.log_action(round_num, 0, 'Fictional participant', 'DO_NOTHING')
            logger.log_round_end(round_num, 1)
        logger.log_simulation_end(2, 2)
        return SimpleNamespace(env=None)
    async def disabled_worker(*args):
        pytest.fail('disabled platform executed')
    namespace = dict(argparse=argparse, asyncio=asyncio, os=os, sys=sys, datetime=datetime,
        load_config=lambda path: json.loads(Path(path).read_text()),
        init_logging_for_simulation=lambda directory: None, SimulationLogManager=SimulationLogManager,
        run_twitter_simulation=controlled_worker if platform == 'twitter' else disabled_worker,
        run_reddit_simulation=controlled_worker if platform == 'reddit' else disabled_worker)
    monkeypatch.setattr(sys, 'argv', ['worker', '--config', str(config_path), '--' + platform + '-only', '--no-wait'])
    exec(compile(ast.Module(body=[main], type_ignores=[]), str(scripts / 'run_parallel_simulation.py'), 'exec'), namespace)
    asyncio.run(namespace['main']())
    assert not (tmp_path / ('reddit' if platform == 'twitter' else 'twitter')).exists()
    monkeypatch.setattr(SimulationRunner, 'RUN_STATE_DIR', str(tmp_path.parent))
    state = SimulationRunState(simulation_id=tmp_path.name, runner_status=RunnerStatus.RUNNING,
        total_rounds=2, twitter_running=platform == 'twitter', reddit_running=platform == 'reddit')
    SimulationRunner._read_action_log(str(tmp_path / platform / 'actions.jsonl'), 0, state, platform)
    assert state.runner_status == RunnerStatus.COMPLETED
    assert state.current_round == 2
    assert state.to_dict()['total_actions_count'] == 2
