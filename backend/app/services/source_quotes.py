"""Map unique whitespace-only quote variants back to exact original text."""
import copy
import re
from .claim_ledger import validate_source


def resolve_source_quotes(ledger, sources, scope):
    result, records = copy.deepcopy(ledger), []
    by_id = {s['evidence_id']: s for s in sources}
    for claim in result:
        quote, citations = claim.get('quote'), claim.get('citation_ids')
        if not isinstance(quote, str) or not quote or not isinstance(citations, list):
            continue
        eligible = [by_id[i] for i in citations if isinstance(i, str) and i in by_id
                    and not validate_source(by_id[i], scope)]
        if any(quote in s['window'] for s in eligible):
            continue
        words = re.findall(r'\S+', quote)
        if not words or len(quote) > 8000:
            continue
        # Every non-whitespace character must be identical. No punctuation,
        # OCR, Unicode, numeric, negation or case normalization is allowed.
        pattern = re.compile(r'\s+'.join(re.escape(w) for w in words))
        matches = [(s, m) for s in eligible for m in pattern.finditer(s['window'])]
        if len(matches) != 1:
            continue
        source, match = matches[0]
        exact = source['window'][match.start():match.end()]
        records.append({'claim_id': claim['claim_id'], 'evidence_id': source['evidence_id'],
                        'model_quote': quote, 'source_quote': exact,
                        'source_start': source['window_start'] + match.start(),
                        'source_end': source['window_start'] + match.end()})
        claim['quote'] = exact
    return result, records
