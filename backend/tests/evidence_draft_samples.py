from app.services.evidence_verifier import text_hash
from app.services.report_agent import Report, ReportOutline, ReportSection, ReportStatus

SCOPE = {'graph_id': 'g1', 'case_id': 'c1', 'case_version_id': 'v1'}
TEXT = 'Alex states that the hearing was postponed until Friday.'


def sample_source():
    return {**SCOPE, 'evidence_id': 'episode:one', 'episode_id': 'one',
            'document_id': 'doc', 'filename': 'record.txt', 'origin': 'source_document',
            'excerpt': TEXT, 'source_hash': text_hash(TEXT), 'window': TEXT,
            'window_hash': text_hash(TEXT), 'window_start': 0, 'window_end': len(TEXT),
            'locator': {'page': 1, 'chunk_index': 0, 'offset_basis': 'stored_chunk'}}


def sample_claim():
    return {'claim_id': 'claim_01', 'schema_version': 1, 'kind': 'attributed_allegation',
            'text': TEXT, 'attribution': 'Alex', 'scope': dict(SCOPE),
            'citation_ids': ['episode:one'], 'premise_claim_ids': [], 'quote': '', 'checks': []}


def sample_report(report_id='report_root'):
    return Report(report_id, 'sim_1', 'g1', 'Analyze the hearing record.', ReportStatus.NEEDS_REVIEW,
                  report_mode='legal_case', created_at='2026-09-21T12:00:00', source_grounding=dict(SCOPE),
                  outline=ReportOutline('Hearing report', 'The hearing is Thursday. Other issues remain open.',
                      [ReportSection('Hearing', content='The hearing is Thursday.'),
                       ReportSection('Other issues', content='Other issues remain open.')]))
