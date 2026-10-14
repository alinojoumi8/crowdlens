"""Deterministic type coverage under a participant cap; no inferred party roles."""
from collections import Counter


class ParticipantSelectionError(ValueError):
    """An explicit roster cannot be fulfilled without changing user intent."""


def validate_participant_ids(value):
    if (not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() for v in value)
            or len(set(value)) != len(value)):
        raise ParticipantSelectionError('participant_ids must be a list of unique non-empty entity IDs')
    return list(value)


def select_participants(entities, settings, *, legal_case=False):
    requested = validate_participant_ids(settings.get('participant_ids', []))
    excluded = set(settings.get('entity_types_exclude') or [])
    included = set(settings.get('entity_types_include') or [])
    eligible = [e for e in entities if e.get_entity_type() not in excluded
                and (not included or included.intersection(
                    label for label in getattr(e, 'labels', [e.get_entity_type()])
                    if label not in ('Entity', 'Node')))]
    groups = {}
    for entity in eligible:
        groups.setdefault(entity.get_entity_type() or 'Unknown', []).append(entity)
    cap = int(settings.get('agent_count') or 0)
    if requested:
        by_id = {getattr(e, 'uuid', None): e for e in eligible}
        missing = [identifier for identifier in requested if identifier not in by_id]
        if missing:
            raise ParticipantSelectionError('Selected participants are missing or excluded by type filters: ' + ', '.join(missing))
        if cap > 0 and len(requested) > cap:
            raise ParticipantSelectionError('Selected participant count exceeds the agent limit; increase the limit or change the selection')
        selected = [by_id[identifier] for identifier in requested]
    elif cap <= 0 or cap >= len(eligible):
        selected = eligible
    else:
        types = sorted(groups)
        for group in groups.values():
            group.sort(key=lambda e: (getattr(e, 'uuid', '') or '', getattr(e, 'name', '') or ''))
        if legal_case:
            # Use explicit graph labels only. Never guess roles from names.
            types.sort(key=lambda t: (0 if t.casefold() == 'plaintiff' else
                                      1 if t.casefold() == 'defendant' else 2))
        selected = []
        offset = 0
        while len(selected) < cap:
            for kind in types:
                if offset < len(groups[kind]):
                    selected.append(groups[kind][offset])
                    if len(selected) == cap:
                        break
            offset += 1
    counts = dict(Counter(e.get_entity_type() or 'Unknown' for e in selected))
    warnings = []
    selected_ids = {id(e) for e in selected}
    omitted = [e for e in eligible if id(e) not in selected_ids]
    if omitted:
        warnings.append('Not selected: ' + ', '.join(str(getattr(e, 'name', 'Unnamed')) for e in omitted))
    if legal_case:
        for role in ('Plaintiff', 'Defendant'):
            if not any(kind.casefold() == role.casefold() for kind in counts):
                warnings.append(f'No {role.lower()} participant selected. Check graph labels, type filters and the participant cap; coverage of both sides is not established.')
    return selected, {'strategy': 'explicit_entities' if requested else 'type_coverage_round_robin',
                      'selected_entities': [{'uuid': getattr(e, 'uuid', None), 'name': getattr(e, 'name', ''),
                                             'entity_type': e.get_entity_type()} for e in selected],
                      'available_by_type': {t: len(g) for t, g in groups.items()},
                      'selected_by_type': counts, 'warnings': warnings}
