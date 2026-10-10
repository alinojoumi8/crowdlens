"""Deterministic type coverage under a participant cap; no inferred party roles."""
from collections import Counter


def select_participants(entities, settings, *, legal_case=False):
    excluded = set(settings.get('entity_types_exclude') or [])
    eligible = [e for e in entities if e.get_entity_type() not in excluded]
    groups = {}
    for entity in eligible:
        groups.setdefault(entity.get_entity_type() or 'Unknown', []).append(entity)
    cap = int(settings.get('agent_count') or 0)
    if cap <= 0 or cap >= len(eligible):
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
    if legal_case:
        for role in ('Plaintiff', 'Defendant'):
            if not any(kind.casefold() == role.casefold() for kind in counts):
                warnings.append(f'No {role.lower()} participant selected. Check graph labels, type filters and the participant cap; coverage of both sides is not established.')
    return selected, {'strategy': 'type_coverage_round_robin', 'available_by_type': {t: len(g) for t, g in groups.items()},
                      'selected_by_type': counts, 'warnings': warnings}
