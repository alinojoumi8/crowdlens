"""Blinded synthetic review packets and strict, disagreement-preserving label import."""
import copy
import json

from scripts.evidence_quality_support import sha256
from app.services.human_review_validation import assess_reviews, json_bytes, rate


def export_packets(directory, fixtures, observations, *, namespace='evidence-quality-v1',
                   candidate_origin='deterministic_substitute', real_model_output=False):
    reviewer, admin = directory / 'reviewer', directory / 'administrator'
    reviewer.mkdir(parents=True)
    admin.mkdir()
    observed = {row['case_id']: row for row in observations}
    mapping, forms = [], []
    for fixture in fixtures:
        if not fixture['human_review_packet']:
            continue
        observation = observed.get(fixture['id'])
        if not observation or not observation.get('after'):
            continue
        packet_id = 'packet_' + sha256((namespace + ':' + fixture['id']).encode())[:12]
        aliases = {source['evidence_id']: 'S' + str(index + 1).zfill(2)
                   for index, source in enumerate(observation['sources'])}
        sources = [{'source_id': aliases[source['evidence_id']], 'document_id': 'D' + str(index + 1).zfill(2),
                    'case_id': 'case-A', 'graph_id': 'graph-A', 'case_version_id': 'version-current',
                    'origin': source['origin'], 'excerpt': source['excerpt'], 'filename': source.get('filename'),
                    'source_sha256': source['source_hash'], 'locator': source['locator']}
                   for index, source in enumerate(observation['sources'])]
        claims = [{key: copy.deepcopy(claim.get(key)) for key in
                   ('claim_id', 'kind', 'text', 'attribution', 'premise_claim_ids')}
                  | {'citation_ids': [aliases.get(identifier, 'UNKNOWN') for identifier in claim.get('citation_ids', [])]}
                  for claim in observation['claims']]
        packet = {'schema_version': 1, 'packet_id': packet_id,
                  'notice': 'Fictional source packet. Candidate origin and expected assertions are withheld. Review only against these sources.',
                  'task': fixture['section']['description'], 'sources': sources,
                  'candidate_section': observation['after']['section'],
                  'candidate_summary': observation['after']['summary'], 'claims': claims}
        citations = list(dict.fromkeys(identifier for c in observation['claims'] for identifier in c.get('citation_ids', [])))
        packet['citation_number_sources'] = {str(index+1): aliases.get(identifier, 'UNKNOWN') for index,identifier in enumerate(citations)}
        if 'candidate_summary_edits' in observation:
            packet['candidate_summary_edits'] = copy.deepcopy(observation['candidate_summary_edits'])
        if 'candidate_summary_claim_ids' in observation:
            packet['candidate_summary_claim_ids'] = copy.deepcopy(observation['candidate_summary_claim_ids'])
        if 'candidate_section_summary' in observation:
            packet['candidate_section_summary'] = copy.deepcopy(observation['candidate_section_summary'])
        if 'candidate_summary_replacements' in observation:
            packet['candidate_summary_replacements'] = copy.deepcopy(observation['candidate_summary_replacements'])
        if 'original_comparison_summary' in observation:
            packet['original_comparison_summary'] = observation['original_comparison_summary']
        content = json_bytes(packet)
        (reviewer / (packet_id + '.json')).write_bytes(content)
        digest = sha256(content)
        forms.append({'schema_version': 1, 'packet_id': packet_id, 'packet_sha256': digest,
                      'reviewer_id': None, 'reviewer_kind': None, 'reviewed_at': None,
                      'review_seconds': None, 'claims': [{'claim_id': claim['claim_id'], 'support': None,
                          'attribution_correct': None, 'citation_support_correct': None, 'rationale': None}
                          for claim in claims], 'reference_facts': None, 'omitted_reference_fact_ids': None,
                      'conflicts_handled': None, 'notes': None})
        mapping.append({'packet_id': packet_id, 'packet_sha256': digest, 'fixture_id': fixture['id'],
                        'candidate_origin': candidate_origin, 'real_model_output': real_model_output,
                        'source_aliases': aliases, 'split': fixture['split']})
    forms.sort(key=lambda row: row['packet_id'])
    mapping.sort(key=lambda row: row['packet_id'])
    (reviewer / 'blank-review-forms.jsonl').write_text(''.join(json.dumps(row, sort_keys=True) + '\n' for row in forms))
    (admin / 'mapping.json').write_bytes(json_bytes(mapping))
    return {'packet_count': len(forms), 'completed_human_reviews': 0, 'status': 'PENDING'}


def import_reviews(packet_directory, forms):
    """Validate explicit provenance; authenticity remains the human collector's responsibility."""
    packets = {}
    for path in sorted(packet_directory.glob('packet_*.json')):
        packet = json.loads(path.read_text())
        packets[packet['packet_id']] = (packet, sha256(path.read_bytes()))
    return assess_reviews(packets, forms)
