"""Complete structurally valid drafts from the persisted ledger, without certification."""
import copy
from .claim_ledger import validate_paragraphs


def complete_claim_coverage(paragraphs, ledger, sources):
    # Malformed links and prose remain blocked; do not repair around validation.
    if validate_paragraphs(paragraphs, ledger, sources):
        return paragraphs, []
    covered = {identifier for paragraph in paragraphs for identifier in paragraph['claim_ids']}
    missing = [claim for claim in ledger if claim['claim_id'] not in covered]
    if len(paragraphs) + len(missing) > 60:
        return paragraphs, []
    rendered, resolutions = copy.deepcopy(paragraphs), []
    for claim in missing:
        index = len(rendered)
        rendered.append({'text': claim['text'], 'kind': claim['kind'], 'claim_ids': [claim['claim_id']]})
        resolutions.append({'paragraph_index': index, 'claim_id': claim['claim_id'],
                            'origin': 'persisted_ledger', 'ledger_text': claim['text']})
    return rendered, resolutions
