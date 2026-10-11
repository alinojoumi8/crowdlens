"""Optional memory must not destroy the only copy of damaged state."""
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import forecast_runtime as memory


@pytest.fixture(autouse=True)
def capture_memory_warnings(caplog):
    memory.logger.addHandler(caplog.handler)
    yield
    memory.logger.removeHandler(caplog.handler)


@pytest.mark.parametrize('kind', ['short', 'summary'])
@pytest.mark.parametrize('raw', [b'{"1":', b'\xff', b'[]', b'{"1":12}',
    b'{"1":[{"content":[]}]}', b'{"1":{"summary":[]}}', b'{"1":NaN}'])
def test_bad_memory_is_retained_and_replaced_only_after_quarantine(tmp_path, kind, raw, caplog):
    filename = memory.SHORT_MEMORY_FILE if kind == 'short' else memory.SUMMARY_MEMORY_FILE
    load = memory.load_short_memory if kind == 'short' else memory.load_memory_summaries
    save = memory.save_short_memory if kind == 'short' else memory.save_memory_summaries
    valid = {'1': [{'round': 1, 'content': 'Retained action', 'action_type': 'POST'}]} if kind == 'short' else {'1': {'round': 5, 'summary': 'Retained summary'}}
    path = tmp_path / filename
    path.write_bytes(raw)
    source = tmp_path / 'actions.jsonl'
    source.write_text('original action evidence\n')
    assert load(str(tmp_path)) == {}
    assert path.read_bytes() == raw
    copies = list(tmp_path.glob(filename + '.corrupt-*'))
    assert len(copies) == 1 and copies[0].read_bytes() == raw
    assert 'memory' in caplog.text.lower() and 'preserved' in caplog.text.lower()
    save(str(tmp_path), valid)
    assert load(str(tmp_path)) == valid
    assert copies[0].read_bytes() == raw
    assert source.read_text() == 'original action evidence\n'


def test_failed_atomic_memory_replacement_keeps_last_complete_state(tmp_path, monkeypatch, caplog):
    before = {'1': [{'content': 'Before interruption'}]}
    memory.save_short_memory(str(tmp_path), before)
    original = (tmp_path / memory.SHORT_MEMORY_FILE).read_bytes()
    def fail(*args, **kwargs):
        raise OSError('synthetic replacement failure')
    monkeypatch.setattr(memory.os, 'replace', fail)
    memory.save_short_memory(str(tmp_path), {'1': [{'content': 'After'}]})
    assert (tmp_path / memory.SHORT_MEMORY_FILE).read_bytes() == original
    assert memory.load_short_memory(str(tmp_path)) == before
    assert sorted(p.name for p in tmp_path.iterdir()) == [memory.SHORT_MEMORY_FILE]
    assert 'failed' in caplog.text.lower()


def test_failed_quarantine_never_allows_overwriting_damaged_file(tmp_path, monkeypatch, caplog):
    path = tmp_path / memory.SHORT_MEMORY_FILE
    path.write_bytes(b'broken memory')
    original_open = memory.os.open
    def denied(path, *args, **kwargs):
        if '.corrupt-' in str(path):
            raise PermissionError('synthetic disk restriction')
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(memory.os, 'open', denied)
    assert memory.load_short_memory(str(tmp_path)) == {}
    memory.record_actions_to_short_memory(str(tmp_path), 'twitter', 1,
        [{'agent_id': 1, 'action_type': 'POST', 'action_args': {'content': 'New'}}])
    assert path.read_bytes() == b'broken memory'
    assert 'preservation failed' in caplog.text.lower() and 'not be saved' in caplog.text.lower()


def test_invalid_new_memory_cannot_truncate_existing_state(tmp_path, caplog):
    good = {'1': [{'content': 'Original'}]}
    memory.save_short_memory(str(tmp_path), good)
    memory.save_short_memory(str(tmp_path), {'1': [{'content': ['invalid']}]})
    assert memory.load_short_memory(str(tmp_path)) == good
    assert 'not saved' in caplog.text.lower()


def test_unreadable_previous_memory_is_not_overwritten(tmp_path, monkeypatch, caplog):
    import builtins
    path = tmp_path / memory.SHORT_MEMORY_FILE
    path.write_bytes(b'{"1":[{"content":"Keep original"}]}')
    before = path.read_bytes()
    def unreadable(filename, mode='r', *args, **kwargs):
        if str(filename) == str(path) and mode == 'rb':
            raise PermissionError('synthetic read failure')
        return builtins.open(filename, mode, *args, **kwargs)
    monkeypatch.setattr(memory, 'open', unreadable, raising=False)
    assert memory.load_short_memory(str(tmp_path)) == {}
    memory.save_short_memory(str(tmp_path), {'1': [{'content': 'New'}]})
    assert path.read_bytes() == before
    assert 'not saved' in caplog.text.lower()


def test_nested_corruption_does_not_crash_next_action_or_summary(tmp_path):
    (tmp_path / memory.SHORT_MEMORY_FILE).write_text(json.dumps({'1': 'invalid list'}))
    (tmp_path / memory.SUMMARY_MEMORY_FILE).write_text(json.dumps({'1': {'summary': []}}))
    memory.record_actions_to_short_memory(str(tmp_path), 'twitter', 5,
        [{'agent_id': 1, 'action_type': 'POST', 'action_args': {'content': 'Recovered action'}}])
    memory.update_memory_summaries(str(tmp_path), 5)
    assert memory.load_short_memory(str(tmp_path))['1'][0]['content'] == 'Recovered action'
    assert 'Recovered action' in memory.load_memory_summaries(str(tmp_path))['1']['summary']
    assert len(list(tmp_path.glob('*.corrupt-*'))) == 2
