from types import SimpleNamespace
from app.services.participant_selection import select_participants


def entity(name, kind):
    return SimpleNamespace(name=name, get_entity_type=lambda: kind)


def test_legal_cap_retains_explicit_both_sides_before_other_types():
    entities = [entity(str(i), 'Company') for i in range(8)] + [entity('D', 'Defendant'), entity('P', 'Plaintiff')]
    selected, info = select_participants(entities, {'agent_count': 2}, legal_case=True)
    assert [e.name for e in selected] == ['P', 'D']
    assert not any('No ' in warning for warning in info['warnings'])
    assert len(entities) == 10


def test_filters_and_insufficient_cap_do_not_invent_a_party():
    entities = [entity('D', 'Defendant'), entity('P', 'Plaintiff')]
    for settings in ({'agent_count': 1}, {'entity_types_exclude': ['Defendant']}):
        selected, info = select_participants(entities, settings, legal_case=True)
        assert len(selected) == 1
        assert any('defendant' in warning for warning in info['warnings'])


def test_type_round_robin_is_repeatable_and_unlimited_preserves_order():
    entities = [entity('A1', 'A'), entity('A2', 'A'), entity('B1', 'B'), entity('C1', 'C')]
    selected, _ = select_participants(entities, {'agent_count': 3})
    assert [e.name for e in selected] == ['A1', 'B1', 'C1']
    assert select_participants(entities, {'agent_count': 3})[0] == selected
    assert select_participants(list(reversed(entities)), {'agent_count': 3})[0] == selected
    assert select_participants(entities, {})[0] == entities


def test_explicit_cedarbrook_people_are_not_replaced_by_municipality():
    people = [entity(name, kind) for name, kind in [
        ('Cedarbrook', 'MunicipalGovernment'), ('Maya', 'ResidentCyclist'),
        ('Leo', 'RetailBusinessOwner'), ('Priya', 'ResidentWithLimitedMobility'),
        ('Daniel', 'CityTransportPlanner')]]
    for item in people:
        item.uuid = item.name.lower()
    requested = ['maya', 'leo', 'priya', 'daniel']
    selected, info = select_participants(people, {'agent_count': 4, 'participant_ids': requested})
    assert [e.uuid for e in selected] == requested
    assert info['strategy'] == 'explicit_entities'
    assert [e['name'] for e in info['selected_entities']] == ['Maya', 'Leo', 'Priya', 'Daniel']
    assert info['warnings'] == ['Not selected: Cedarbrook']


def test_explicit_roster_fails_closed_instead_of_truncating_or_falling_back():
    import pytest
    from app.services.participant_selection import ParticipantSelectionError
    person = entity('Leo', 'RetailBusinessOwner')
    person.uuid = 'leo'
    for settings in [
        {'participant_ids': ['missing']},
        {'participant_ids': ['leo'], 'entity_types_exclude': ['RetailBusinessOwner']},
        {'participant_ids': ['leo'], 'entity_types_include': ['Resident']},
        {'participant_ids': ['leo', 'leo']},
        {'participant_ids': 'leo'},
        {'participant_ids': [None]},
    ]:
        with pytest.raises(ParticipantSelectionError):
            select_participants([person], settings)
    other = entity('Maya', 'Resident'); other.uuid = 'maya'
    with pytest.raises(ParticipantSelectionError, match='exceeds'):
        select_participants([person, other], {'participant_ids': ['leo', 'maya'], 'agent_count': 1})


def test_normalization_preserves_ids_without_parsing_names():
    from app.models.case import normalize_prediction_settings
    assert normalize_prediction_settings({'participant_ids': ['leo', 'maya']})['participant_ids'] == ['leo', 'maya']
