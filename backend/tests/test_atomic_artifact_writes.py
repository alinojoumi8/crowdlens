"""State files are replaced whole, so a reader or a crash never sees half a file."""
import json
import os

import pytest

from app.services import quota_io
from app.services.simulation_manager import SimulationManager, SimulationState


def test_write_text_replaces_the_file_and_leaves_no_temporary_file(tmp_path):
    target = tmp_path / 'state.json'
    target.write_text('old', encoding='utf-8')

    quota_io.write_text(str(target), 'new')

    assert target.read_text(encoding='utf-8') == 'new'
    assert os.listdir(tmp_path) == ['state.json']


def test_failed_write_keeps_the_previous_file(tmp_path, monkeypatch):
    target = tmp_path / 'state.json'
    target.write_text('old', encoding='utf-8')
    monkeypatch.setattr(quota_io.os, 'replace', lambda *args: (_ for _ in ()).throw(OSError('disk full')))

    with pytest.raises(OSError):
        quota_io.write_text(str(target), 'new')

    assert target.read_text(encoding='utf-8') == 'old'
    assert os.listdir(tmp_path) == ['state.json']


def test_simulation_state_survives_a_failed_save(tmp_path, monkeypatch):
    monkeypatch.setattr(SimulationManager, 'SIMULATION_DATA_DIR', str(tmp_path))
    manager = SimulationManager()
    state = SimulationState(simulation_id='sim_atomic', project_id='proj', graph_id='graph')
    manager._save_simulation_state(state)
    saved = (tmp_path / 'sim_atomic' / 'state.json').read_text(encoding='utf-8')
    monkeypatch.setattr(quota_io.os, 'replace', lambda *args: (_ for _ in ()).throw(OSError('disk full')))

    with pytest.raises(OSError):
        manager._save_simulation_state(state)

    assert json.loads((tmp_path / 'sim_atomic' / 'state.json').read_text(encoding='utf-8'))['simulation_id'] == 'sim_atomic'
    assert (tmp_path / 'sim_atomic' / 'state.json').read_text(encoding='utf-8') == saved
