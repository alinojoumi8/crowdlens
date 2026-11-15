"""A run that loses task ownership (stop or spend limit) must stop persona generation.

Before the fix, every remaining persona retried three times and then got a
rule-based persona, so a halted run kept working for minutes.
"""
import threading

import pytest

from app.services.entity_reader import EntityNode
from app.services.oasis_profile_generator import OasisProfileGenerator
from app.services.task_execution import OwnershipLost
from app.services.workflow_execution import WorkflowHalt


class HaltedClient:
    def __init__(self):
        self.calls = 0
        self.lock = threading.Lock()

    def chat(self, **kwargs):
        with self.lock:
            self.calls += 1
        raise OwnershipLost('task_ownership_lost')


def entities(count):
    return [EntityNode(uuid=f'e{i}', name=f'Company {i}', labels=['Entity', 'Organization'],
                       summary=f'Company {i} sells payments.', attributes={}) for i in range(count)]


def generator(monkeypatch, client):
    gen = OasisProfileGenerator(api_key='test', base_url='http://llm.invalid', model_name='test')
    gen.client = client
    monkeypatch.setattr('time.sleep', lambda seconds: None)
    return gen


def test_lost_ownership_is_not_retried_or_replaced(monkeypatch):
    client = HaltedClient()
    gen = generator(monkeypatch, client)
    entity = entities(1)[0]

    with pytest.raises(OwnershipLost):
        gen.generate_profile_from_entity(entity, user_id=0, use_llm=True)

    assert client.calls == 1


class FirstCallHalts:
    """The first call halts the run; every other call blocks until released."""

    def __init__(self, halt):
        self.halt = halt
        self.calls = 0
        self.lock = threading.Lock()
        self.release = threading.Event()

    def chat(self, **kwargs):
        with self.lock:
            self.calls += 1
            first = self.calls == 1
        if first:
            raise self.halt
        self.release.wait(10)
        raise self.halt


# A stop or time limit surfaces as OwnershipLost; a spend limit as WorkflowHalt.
@pytest.mark.parametrize('halt', [OwnershipLost('task_ownership_lost'), WorkflowHalt('spend_limit', 'wf_test')])
def test_a_halt_stops_the_batch_without_waiting_for_running_calls(monkeypatch, halt):
    client = FirstCallHalts(halt)
    gen = generator(monkeypatch, client)
    outcome = {}

    def run():
        try:
            gen.generate_profiles_from_entities(entities(20), use_llm=True, parallel_count=2)
        except (OwnershipLost, WorkflowHalt) as exc:
            outcome['error'] = exc

    caller = threading.Thread(target=run)
    caller.start()
    caller.join(5)
    try:
        # The halt reached the caller while sibling calls were still blocked.
        assert not caller.is_alive()
        assert outcome.get('error') is halt
    finally:
        client.release.set()
        caller.join(5)

    # Both workers are blocked, so no queued persona can start after the cancel:
    # at most the failed call plus one blocked call per worker. Without the fix: 60.
    assert client.calls <= 3
