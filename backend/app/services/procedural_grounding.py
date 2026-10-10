"""Conservative cover relief and document-scoped notice roles, not fact verification."""
import hashlib
import re
from .pdf_source_pages import complete_pages


def marked_source_openings(sources):
    """Recover explicit, complete page-one spans from frozen original chunks.

    A missing page field, chunk zero, or filename alone is never page evidence.
    Scope is checked again by build_grounding. Keep source offsets for audit.
    """
    openings = []
    for source in sources:
        text = source.get('excerpt') or ''
        if not isinstance(text, str):
            continue
        for page, start, end in complete_pages(text):
            if page == 1:
                openings.append({**source, 'uuid': source.get('episode_id'),
                    'page': 1, 'data': text, 'locator_basis': 'pdf_page_markers',
                    'page_start': start, 'page_end': end,
                    'chunk_source_hash': source.get('source_hash')})
    return openings


def build_grounding(episodes, graph_id, case_id, case_version_id):
    anchors = []
    notices = []
    total_chars = 0
    incomplete = False
    for episode in episodes:
        if (episode.get('origin', 'source_document') != 'source_document'
                or not case_id or not case_version_id or episode.get('graph_id') != graph_id
                or episode.get('case_id') != case_id or episode.get('case_version_id') != case_version_id
                or not episode.get('document_id') or episode.get('page') != 1):
            continue
        text = episode.get('data') or ''
        if not isinstance(text, str) or len(text) > 12000 or total_chars + len(text) > 24000:
            incomplete = True
            continue
        total_chars += len(text)
        if re.search(r'(?m)^\[PDF page [1-9][0-9]*\]', text):
            pages = [(start, end) for page, start, end in complete_pages(text) if page == 1]
            if len(pages) != 1:
                incomplete = True
                continue
            start, end = pages[0]
            text = text[start:end]
        # A caption is not a mover declaration. Read only an explicit declaration
        # after a notice heading, within the same scoped page-one source chunk.
        heading = re.search(r'(?im)^\s*NOTICE\s+OF\s+(CROSS[-\s]+)?MOTION\s*$', text)
        if heading:
            body = text[heading.end():]
            declarations = re.findall(
                r'(?im)^\s*THE\s+(PLAINTIFFS?|DEFENDANTS?|APPLICANTS?|RESPONDENTS?)\b'
                r"((?:(?-i:[A-Z0-9 ,\n\r\t()'’&/\-])|\.(?=\s*(?:,|will\b))|\band\b){0,600}?)"
                r'\bwill\s+make\s+a\s+motion\b', body)
            declarations = [(role, names) for role, names in declarations if not re.search(
                r'\b(plaintiffs?|defendants?|applicants?|respondents?|not|oppose|opposes|who|whether|if|deny|denies)\b', names, re.I)]
            if not declarations:
                incomplete = True
            for declared, _ in declarations:
                notices.append({'moving_role': declared.lower().rstrip('s') + 's',
                    'notice_kind': 'cross_motion' if heading[1] else 'motion',
                    'document_id': episode['document_id'], 'episode_id': episode.get('uuid'),
                    'page': 1, 'excerpt': text,
                    'locator_basis': episode.get('locator_basis', 'stored_page'),
                    'page_start': episode.get('page_start'), 'page_end': episode.get('page_end'),
                    'chunk_source_hash': episode.get('chunk_source_hash'),
                    'source_hash': hashlib.sha256(text.encode()).hexdigest()})
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
    notice_roles = {}
    for notice in notices:
        notice_roles.setdefault(notice['document_id'], set()).add(notice['moving_role'])
    conflicting = any(len(roles) != 1 for roles in notice_roles.values())
    conflicting |= any(a['document_id'] in notice_roles and a['moving_role'] not in notice_roles[a['document_id']] for a in anchors)
    # Mixed cover/notice packets need a document-scoped relief checker before
    # the legacy global cover check can safely be applied to them.
    status = ('ambiguous' if incomplete or conflicting or (anchors and notices) else 'anchored' if len(identities) == 1
              else 'ambiguous' if identities else 'notice_anchored' if notices else 'unavailable')
    return {'status': status, 'graph_id': graph_id, 'case_id': case_id,
            'case_version_id': case_version_id, 'anchors': anchors, 'notice_anchors': notices}


def notice_attribution_issues(content, notices):
    """Check narrow affirmative notice labels with one cited original document.

    Two sides can each bring a motion. Never bind a global moving/opposing role
    or requested relief from these notice declarations.
    """
    roles = {n['document_id']: n['moving_role'] for n in notices}
    issues = []
    for paragraph in re.split(r'\n\s*\n', content):
        # Multiple document references leave binding ambiguous; do not guess.
        documents = set(re.findall(r'\[(doc_[A-Za-z0-9_-]+)\]', paragraph))
        if len(documents) != 1 or not documents <= roles.keys():
            continue
        document = next(iter(documents))
        prefix = paragraph[:paragraph.index(f'[{document}]')].strip()
        sentences = [s for s in re.split(r'(?<=[.!?])\s+', prefix) if s.strip()]
        # A citation following several assertions can support only one of them.
        # Also exclude within-sentence comparisons even with just one citation.
        if len(sentences) != 1:
            continue
        for sentence in sentences:
            mentioned = {r.lower().rstrip('s') + 's' for r in re.findall(
                r'\b(plaintiffs?|defendants?|applicants?|respondents?)\b', sentence, re.I)}
            if len(mentioned) != 1:
                continue
            if re.search(r'\b(not|never|whether|if|could|might|original|earlier|prior)\b', sentence, re.I):
                continue
            # Quoted source text is not a draft attribution assertion.
            sentence = re.sub(r'["“][^"”]*["”]', '', sentence)
            if sentence.lstrip().startswith('>'):
                continue
            claimed = re.findall(
                r'\b(plaintiffs?|defendants?|applicants?|respondents?)'
                r'(?:[’\']s?\s+notice\b|\s+will\s+make\s+a\s+motion\b'
                r'|\s+(?:signed|filed|served)\s+(?:this|the)\s+notice\b)', sentence, re.I)
            for role in claimed:
                role = role.lower().rstrip('s') + 's'
                if role != roles[document]:
                    issues.append({'code': 'procedural_role_conflict', 'requires_review': True,
                        'blocking': False, 'document_id': document, 'page': 1,
                        'message': f'Draft labels the cited notice as {role}, but its explicit mover declaration identifies {roles[document]}. Review original document page 1.'})
    return issues


def attribution_issues(content, grounding):
    status = grounding.get('procedural_status', grounding.get('status'))
    notices = grounding.get('notice_anchors') or []
    if status == 'notice_anchored' and notices:
        return notice_attribution_issues(content, notices)
    if status != 'anchored' or not grounding.get('anchors'):
        return [{'code': 'procedural_source_unavailable', 'requires_review': True, 'blocking': False,
                 'message': 'The procedural check could not establish an explicit cover role and relief or document-scoped notice mover. '
                            'Captions, conflicting declarations, or incomplete source retrieval do not satisfy this narrow check. '
                            'Review procedural attribution against the original documents; this warning is not a finding of misattribution.'}]
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
    return notice_attribution_issues(content, notices)
