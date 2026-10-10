from types import SimpleNamespace
from app.services.participant_selection import select_participants


def entity(name, kind):
    return SimpleNamespace(name=name, get_entity_type=lambda: kind)


def test_legal_cap_retains_explicit_both_sides_before_other_types():
    entities = [entity(str(i), 'Company') for i in range(8)] + [entity('D', 'Defendant'), entity('P', 'Plaintiff')]
    selected, info = select_participants(entities, {'agent_count': 2}, legal_case=True)
    assert [e.name for e in selected] == ['P', 'D']
    assert info['warnings'] == []
    assert len(entities) == 10


def test_filters_and_insufficient_cap_do_not_invent_a_party():
    entities = [entity('D', 'Defendant'), entity('P', 'Plaintiff')]
    for settings in ({'agent_count': 1}, {'entity_types_exclude': ['Defendant']}):
        selected, info = select_participants(entities, settings, legal_case=True)
        assert len(selected) == 1
        assert len(info['warnings']) == 1
        assert 'defendant' in info['warnings'][0]


def test_type_round_robin_is_repeatable_and_unlimited_preserves_order():
    entities = [entity('A1', 'A'), entity('A2', 'A'), entity('B1', 'B'), entity('C1', 'C')]
    selected, _ = select_participants(entities, {'agent_count': 3})
    assert [e.name for e in selected] == ['A1', 'B1', 'C1']
    assert select_participants(entities, {'agent_count': 3})[0] == selected
    assert select_participants(list(reversed(entities)), {'agent_count': 3})[0] == selected
    assert select_participants(entities, {})[0] == entities
