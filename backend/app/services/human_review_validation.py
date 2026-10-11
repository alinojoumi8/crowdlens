"""Shared human review rubric for app persistence and offline evaluation imports."""
import copy
import json
import math


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n').encode()


def rate(numerator, denominator):
    return {'numerator': numerator, 'denominator': denominator,
            'rate': numerator / denominator if denominator else None}


def assess_reviews(packets, forms):
    """Validate and score explicitly attributed human forms against frozen packets."""
    accepted, pending, seen = [], [], set()
    for original in forms:
        row = copy.deepcopy(original)
        if row.get('packet_id') not in packets:
            raise ValueError('unknown_packet')
        packet, digest = packets[row['packet_id']]
        if row.get('packet_sha256') != digest:
            raise ValueError('packet_hash_mismatch')
        if row.get('schema_version') != 1 or not isinstance(row.get('claims'), list):
            raise ValueError('invalid_review_schema')
        expected = {claim['claim_id'] for claim in packet['claims']}
        identifiers = [claim.get('claim_id') for claim in row['claims'] if isinstance(claim, dict)]
        if len(identifiers) != len(row['claims']) or len(identifiers) != len(set(identifiers)) or set(identifiers) != expected:
            raise ValueError('claim_coverage_mismatch')
        if any(not {'claim_id', 'support', 'attribution_correct', 'citation_support_correct', 'rationale'} <= set(claim)
               for claim in row['claims']):
            raise ValueError('missing_claim_fields')
        any_label = any(claim.get(key) is not None for claim in row['claims']
                        for key in ('support', 'attribution_correct', 'citation_support_correct'))
        any_label = any_label or any(row.get(key) is not None for key in
                                     ('reference_facts', 'omitted_reference_fact_ids', 'conflicts_handled', 'review_seconds'))
        if row.get('reviewer_id') is None and not any_label and row.get('reviewer_kind') is None and row.get('reviewed_at') is None:
            pending.append(row)
            continue
        if row.get('reviewer_kind') not in {'human', 'expert_human'}:
            raise ValueError('human_provenance_required')
        if not isinstance(row.get('reviewer_id'), str) or not row['reviewer_id'].strip():
            raise ValueError('reviewer_identity_required')
        from datetime import datetime
        try:
            timestamp = datetime.fromisoformat(row['reviewed_at'].replace('Z', '+00:00'))
            if timestamp.tzinfo is None:
                raise ValueError('timezone_required')
        except (KeyError, TypeError, AttributeError, ValueError) as exc:
            raise ValueError('review_timestamp_required') from exc
        identity = (row['packet_id'], row['reviewer_id'])
        if identity in seen:
            raise ValueError('duplicate_reviewer_packet')
        seen.add(identity)
        seconds = row.get('review_seconds')
        if seconds is not None and (type(seconds) not in (float, int) or not math.isfinite(seconds) or seconds < 0):
            raise ValueError('invalid_measured_review_time')
        for claim in row['claims']:
            if claim.get('support') not in {None, 'supported', 'unsupported', 'ambiguous', 'conflicting'}:
                raise ValueError('invalid_support_label')
            for key in ('attribution_correct', 'citation_support_correct'):
                if claim.get(key) is not None and type(claim[key]) is not bool:
                    raise ValueError('invalid_boolean_label')
            if any(claim.get(key) is not None for key in ('support', 'attribution_correct', 'citation_support_correct')):
                if not isinstance(claim.get('rationale'), str) or not claim['rationale'].strip():
                    raise ValueError('label_rationale_required')
        if row.get('conflicts_handled') is not None and type(row['conflicts_handled']) is not bool:
            raise ValueError('invalid_conflict_label')
        reference, omissions = row.get('reference_facts'), row.get('omitted_reference_fact_ids')
        if (reference is None) != (omissions is None):
            raise ValueError('omissions_require_reference_assessment')
        if reference is not None:
            if not isinstance(reference, list) or not isinstance(omissions, list):
                raise ValueError('invalid_reference_assessment')
            facts = [fact.get('fact_id') for fact in reference if isinstance(fact, dict)
                     and isinstance(fact.get('fact_id'), str) and isinstance(fact.get('text'), str)
                     and fact['fact_id'].strip() and fact['text'].strip()]
            if len(facts) != len(reference) or len(facts) != len(set(facts)):
                raise ValueError('invalid_reference_facts')
            if any(not isinstance(identifier, str) or identifier not in facts for identifier in omissions) or len(omissions) != len(set(omissions)):
                raise ValueError('invalid_omission_ids')
        meaningful = any(claim.get(field) is not None for claim in row['claims']
                         for field in ('support', 'attribution_correct', 'citation_support_correct'))
        if not meaningful and reference is None and row.get('conflicts_handled') is None:
            pending.append(row)
            continue
        accepted.append(row)
    claims = [claim for row in accepted for claim in row['claims']]
    judged = [claim for claim in claims if claim['support'] in {'supported', 'unsupported'}]
    attribution = [claim['attribution_correct'] for claim in claims if type(claim.get('attribution_correct')) is bool]
    citations = [claim['citation_support_correct'] for claim in claims if type(claim.get('citation_support_correct')) is bool]
    reference_rows = [row for row in accepted if row.get('reference_facts') is not None]
    seconds = [row['review_seconds'] for row in accepted if row.get('review_seconds') is not None]
    labeled_packets = {row['packet_id'] for row in accepted if row['claims'] and all(
        claim.get(field) is not None for claim in row['claims']
        for field in ('support', 'attribution_correct', 'citation_support_correct'))}
    disagreements = []
    for packet_id in packets:
        for claim_id in {claim['claim_id'] for claim in packets[packet_id][0]['claims']}:
            for field in ('support', 'attribution_correct', 'citation_support_correct'):
                judgments = [{'reviewer_id': row['reviewer_id'], 'value': claim[field]}
                             for row in accepted if row['packet_id'] == packet_id for claim in row['claims']
                             if claim['claim_id'] == claim_id and claim.get(field) is not None]
                if len({json.dumps(item['value']) for item in judgments}) > 1:
                    disagreements.append({'packet_id': packet_id, 'claim_id': claim_id, 'field': field,
                                          'judgments': judgments})
    return {'schema_version': 1, 'reviewed_packets': len(labeled_packets),
            'review_rows': len(accepted), 'pending_forms': len(pending), 'packet_count': len(packets),
            'status': 'PENDING' if not accepted else 'PARTIAL' if len(labeled_packets) < len(packets) else 'LABELS_IMPORTED',
            'unsupported_claims_per_review': rate(sum(claim['support'] == 'unsupported' for claim in judged), len(judged)),
            'attribution_correct_per_review': rate(sum(attribution), len(attribution)),
            'citation_support_correct_per_review': rate(sum(citations), len(citations)),
            'ambiguous_or_conflicting_claims': sum(claim['support'] in {'ambiguous', 'conflicting'} for claim in claims),
            'omissions_per_reference_fact_review': rate(sum(len(row['omitted_reference_fact_ids']) for row in reference_rows),
                                                       sum(len(row['reference_facts']) for row in reference_rows)),
            'measured_review_seconds': {'count': len(seconds), 'total': sum(seconds) if seconds else None,
                                        'mean': sum(seconds) / len(seconds) if seconds else None},
            'reviews': accepted, 'pending': pending, 'disagreements': disagreements,
            'real_model_quality': None,
            'limitations': ['Candidate origin must be established from the administrator mapping and collection receipts; labels alone do not establish model provenance.',
                            'Rates pool individual reviewer judgments, not adjudicated ground truth.',
                            'Imported labels do not imply completed adjudication or human sign-off.',
                            'Ambiguous and conflicting support is preserved and excluded from binary support denominator.',
                            'Provenance fields cannot establish reviewer authenticity; collector verification remains required.']}
