"""Offline paired evaluation; independent labels are inputs, never inferred."""
import argparse
import copy
import json
import math
from pathlib import Path

LABELS = ('factual_correct', 'attribution_correct', 'citation_valid', 'quote_valid')
INDEPENDENT = {'human', 'expert', 'independent_review'}


def rate(numerator, denominator):
    return {'numerator': numerator, 'denominator': denominator,
            'rate': numerator / denominator if denominator else None}


def score_claims(claims):
    result = {}
    for label in LABELS:
        labeled = [c for c in claims if type(c.get(label)) is bool]
        result[label] = rate(sum(c[label] for c in labeled), len(labeled))
    labeled = [c for c in claims if type(c.get('factual_correct')) is bool]
    critical = [c for c in labeled if c.get('critical') is True]
    supported = [c for c in labeled if c.get('supported') is True]
    result.update(labeled_count=len(labeled), unlabeled_count=len(claims)-len(labeled),
                  accuracy=result['factual_correct']['rate'],
                  critical_errors=rate(sum(not c['factual_correct'] for c in critical), len(critical)),
                  false_supported=rate(sum(not c['factual_correct'] for c in supported), len(supported)),
                  unresolved_count=sum(c.get('supported') is not True for c in claims))
    return result


def measured(value):
    return value if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None


def side_score(side, reviewed, prices):
    claims = copy.deepcopy(side.get('claims', []))
    for claim in claims:
        if not reviewed or claim.get('label_source', 'independent_review') not in INDEPENDENT:
            for key in LABELS:
                claim[key] = None
    result = score_claims(claims)
    relevant = set(side.get('relevant_source_ids') or []) if reviewed else set()
    retrieved = set(side.get('retrieved_source_ids') or [])
    result['retrieval_recall'] = rate(len(retrieved & relevant), len(relevant))
    result['important_omissions'] = measured(side.get('important_omissions')) if reviewed else None
    result['review_seconds'] = measured(side.get('review_seconds')) if reviewed else None
    result['elapsed_seconds'] = measured(side.get('elapsed_seconds'))
    calls = (side.get('usage') or {}).get('calls', [])
    result['provider_requests'] = sum(c.get('attempt_count', 1) for c in calls)
    result['cost'] = None
    if prices and calls:
        cost = 0
        for call in calls:
            price = prices.get(call.get('model'), {})
            counts = [measured(call.get(k)) for k in ('input_tokens','output_tokens')]
            tariffs = [measured(price.get(k)) for k in ('input_per_million','output_per_million')]
            if None in counts + tariffs:
                break
            cost += sum(count * tariff / 1_000_000 for count, tariff in zip(counts, tariffs))
        else:
            result['cost'] = cost
    return result, claims


def evaluate_pairs(rows, prices=None):
    pairs, pooled, reviewed_count, seen = [], {'baseline':[], 'proposed':[]}, 0, set()
    for row in rows:
        identity = (row['case_id'], row['split'])
        if identity in seen or not all(isinstance(row.get(side), dict) for side in pooled):
            raise ValueError('duplicate_or_unpaired_case')
        seen.add(identity)
        reviewed = row.get('reviewed') is True and row.get('label_source') in INDEPENDENT
        reviewed_count += reviewed
        result = {'case_id': row['case_id'], 'split': row['split'], 'independently_reviewed': reviewed}
        for side in pooled:
            result[side], claims = side_score(row[side], reviewed, prices)
            pooled[side].extend(claims)
        a, b = result['baseline']['accuracy'], result['proposed']['accuracy']
        result['accuracy_delta'] = b-a if a is not None and b is not None else None
        pairs.append(result)
    totals = {side: score_claims(claims) for side, claims in pooled.items()}
    for side in pooled:
        totals[side]['retrieval_recall'] = rate(sum(pair[side]['retrieval_recall']['numerator'] for pair in pairs),
                                                sum(pair[side]['retrieval_recall']['denominator'] for pair in pairs))
    return {'schema_version':1, 'pair_count':len(pairs), 'independently_reviewed_pairs':reviewed_count,
            'unreviewed_pairs':len(pairs)-reviewed_count, 'pairs':pairs, 'pooled':totals,
            'limitations':['Input labels are supplied independently; model agreement is not ground truth.',
                           'Synthetic and unreviewed labels are excluded from quality denominators.',
                           'No cost or human review time is estimated from token counts.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--prices', type=Path, help='Explicit model prices per million input/output tokens')
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.input.read_text().splitlines() if line.strip()]
    prices = json.loads(args.prices.read_text()) if args.prices else None
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evaluate_pairs(rows, prices), indent=2, allow_nan=False)+'\n')


if __name__ == '__main__':
    main()
