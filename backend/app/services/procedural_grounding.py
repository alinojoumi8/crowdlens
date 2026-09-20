"""Conservative source-cover anchors, not general legal fact verification."""
import hashlib
import re


def build_grounding(episodes, graph_id, case_id, case_version_id):
    anchors = []
    total_chars = 0
    incomplete = False
    for episode in episodes:
        if (not case_id or not case_version_id or episode.get('graph_id') != graph_id
                or episode.get('case_id') != case_id or episode.get('case_version_id') != case_version_id
                or not episode.get('document_id') or episode.get('page') != 1):
            continue
        text = episode.get('data') or ''
        if not isinstance(text, str) or len(text) > 12000 or total_chars + len(text) > 24000:
            incomplete = True
            continue
        total_chars += len(text)
        # Recognize only explicit cover labels. Do not infer a mover from the caption.
        match = re.search(r'\bMOTION\s+RECORD\s+OF\s+THE\s+(PLAINTIFFS?|DEFENDANTS?|APPLICANTS?|RESPONDENTS?)\b', text, re.I)
        relief = re.search(r'\bmotion\s+to\s+(set\s+aside|discharge|vary|dismiss)\b', text, re.I)
        if not match or not relief:
            continue
        role = match[1].lower().rstrip('s') + 's'
        anchors.append({'moving_role': role, 'relief': ' '.join(relief[1].lower().split()),
                        'document_id': episode['document_id'], 'episode_id': episode.get('uuid'),
                        'page': 1, 'excerpt': text, 'source_hash': hashlib.sha256(text.encode()).hexdigest()})
    identities = {(a['moving_role'], a['relief']) for a in anchors}
    return {'status': 'ambiguous' if incomplete else 'anchored' if len(identities) == 1 else 'ambiguous' if identities else 'unavailable',
            'graph_id': graph_id, 'case_id': case_id, 'case_version_id': case_version_id, 'anchors': anchors}


def attribution_issues(content, grounding):
    if grounding.get('status') != 'anchored':
        return [{'code': 'procedural_source_unavailable', 'requires_review': True, 'blocking': False,
                 'message': 'An unambiguous source-cover role could not be established. Review procedural attribution against the original documents.'}]
    anchor = grounding['anchors'][0]
    others = {'plaintiffs', 'defendants', 'applicants', 'respondents'} - {anchor['moving_role']}
    relief = re.escape(anchor['relief']).replace(r'\ ', r'\s+')
    # Narrow positive constructions only; opposition, original relief, and other
    # unrecognized prose remain outside this deterministic check's coverage.
    for role in sorted(others):
        role_pattern = re.escape(role.rstrip('s')) + r's?'
        pattern = (rf'\b{role_pattern}(?:[’\']s?|\s)*\s*'
                   rf'(?:(?:seek|seeks|seeking|sought|move|moves|moved)\s+to\s+{relief}'
                   rf'|motion\s+to\s+{relief})\b')
        if re.search(pattern, content, re.I):
            return [{'code': 'procedural_role_conflict', 'requires_review': True, 'blocking': False,
                     'message': f"Draft attributes {anchor['relief']} relief to {role}, but the source cover identifies {anchor['moving_role']}. Review the original document page 1.",
                     'document_id': anchor['document_id'], 'page': 1}]
    return []
