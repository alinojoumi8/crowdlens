"""Account for retrieved windows without treating citations as entailment."""
from .claim_ledger import finding


def source_coverage(claims, exclusions, sources):
    known = {source['evidence_id'] for source in sources}
    cited = {identifier for claim in claims if isinstance(claim, dict)
             for identifier in (claim.get('citation_ids') if isinstance(claim.get('citation_ids'), list) else [])
             if isinstance(identifier, str)}
    if not isinstance(exclusions, list) or len(exclusions) > 30:
        return [finding('invalid_source_exclusions')]
    excluded = set()
    for item in exclusions:
        if (not isinstance(item, dict) or set(item) != {'evidence_id', 'reason'}
                or not isinstance(item['evidence_id'], str) or item['evidence_id'] not in known
                or item['evidence_id'] in cited or item['evidence_id'] in excluded
                or not isinstance(item['reason'], str) or not item['reason'].strip() or len(item['reason']) > 1000):
            return [finding('invalid_source_exclusions')]
        excluded.add(item['evidence_id'])
    return [{**finding('unaccounted_source_window'), 'evidence_id': identifier}
            for identifier in sorted(known - cited - excluded)]
