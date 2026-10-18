"""Bound revised summaries and derive their references from frozen ledger inputs."""
import html
import re

SUMMARY_FORMAT = 'concise-linked-v1'


def validate_concise_summary(record):
    # Retained proposals keep their original contract, including audit retries.
    if 'summary_format' not in record:
        return
    if record['summary_format'] != SUMMARY_FORMAT:
        raise ValueError('invalid_summary_format')
    edits = record['summary_edits']
    if sum(len(edit['new_text']) for edit in edits) > 600:
        raise ValueError('summary_too_long')
    for span in record.get('before', {}).get('summary_scope_contract', {}).get('editable_spans', []):
        selected = span['text']
        for edit in sorted(edits, key=lambda item: item['start'], reverse=True):
            if span['start'] <= edit['start'] <= edit['end'] <= span['end']:
                start, end = edit['start'] - span['start'], edit['end'] - span['start']
                selected = selected[:start] + edit['new_text'] + selected[end:]
        if len(selected) > 600:
            raise ValueError('summary_too_long')
    for edit in edits:
        if not edit['new_text'].strip() or '\n' in edit['new_text'] or '\r' in edit['new_text']:
            raise ValueError('summary_requires_short_prose')


def summary_sources(record):
    """Resolve direct citations and analysis premises, never model-provided URLs."""
    claims = {claim['claim_id']: claim for claim in record['ledger']}
    sources = {source['evidence_id']: source for source in record['sources']}

    def citations(identifier, path=()):
        if identifier in path or identifier not in claims:
            raise ValueError('invalid_summary_claim_chain')
        claim = claims[identifier]
        result = list(claim['citation_ids'])
        for premise in claim['premise_claim_ids']:
            result.extend(citations(premise, (*path, identifier)))
        return result

    passages = []
    shift = 0
    for edit in sorted(record['summary_edits'], key=lambda edit: edit['start']):
        identifiers = list(dict.fromkeys(identifier for claim in edit['claim_ids'] for identifier in citations(claim)))
        if not identifiers or any(identifier not in sources for identifier in identifiers):
            raise ValueError('missing_summary_source')
        start = edit['start'] + shift
        passages.append({'text': edit['new_text'], 'start': start, 'end': start + len(edit['new_text']),
                         'sources': [sources[identifier] for identifier in identifiers]})
        shift += len(edit['new_text']) - (edit['end'] - edit['start'])
    return passages


def revision_summary_sources(parent, record):
    """Keep inherited links only while their exact passage and position survive."""
    passages = summary_sources(record)
    edits = record['summary_edits']
    for passage in parent.revision.get('summary_sources', []):
        start, end = passage.get('start'), passage.get('end')
        if (type(start) is not int or type(end) is not int or not 0 <= start < end <= len(parent.outline.summary)
                or parent.outline.summary[start:end] != passage['text']
                or any(edit['start'] < end and edit['end'] > start for edit in edits)
                or any(start < edit['start'] < end for edit in edits)):
            continue
        shift = sum(len(edit['new_text']) - (edit['end'] - edit['start']) for edit in edits if edit['end'] <= start)
        passages.append({**passage, 'start': start + shift, 'end': end + shift})
    return sorted(passages, key=lambda passage: passage['start'])


def _plain(text):
    # Frozen filenames and excerpts are untrusted Markdown/HTML, not markup.
    return re.sub(r'([\\`*_{}\[\]()#+.!|>~-])', r'\\\1', html.escape(str(text), quote=True))


def summary_sources_markdown(passages):
    if not passages:
        return ''
    lines = ['<a id="revised-summary-sources"></a>', '## Sources for revised summary passages',
             'These links cover the revised passages only. AI checks may come from an earlier revision and still require human review.']
    for number, passage in enumerate(passages, 1):
        links = ' '.join(f'[Source {index}](#summary-source-{number}-{index})' for index in range(1, len(passage['sources']) + 1))
        lines.append(f"{_plain(passage['text'])} {links}")
        for index, source in enumerate(passage['sources'], 1):
            locator = source.get('locator') or {}
            page = str(locator.get('page', 'not recorded'))
            if locator.get('page_end') is not None and locator.get('page_end') != locator.get('page'):
                page += '–' + str(locator['page_end'])
            label = source.get('filename') or source['document_id']
            lines.extend([f'<a id="summary-source-{number}-{index}"></a>',
                          f"Source {index}: {_plain(label)} · page {_plain(page)}",
                          '> ' + _plain(source.get('window') or source.get('excerpt') or '').replace('\n', '\n> ')])
    return '\n\n'.join(lines) + '\n\n'


def report_prose_for_validation(report):
    """Exclude only an exact server-rendered appendix backed by frozen cards.

    Report prose, including quoted text and any altered appendix, remains checked.
    Source excerpts are reference material, not newly authored report assertions.
    """
    content = report.markdown_content or ''
    passages = report.revision.get('summary_sources', [])
    if not passages or not report.outline:
        return content
    cards = [card for section in report.outline.sections for card in section.evidence_cards]
    for passage in passages:
        start, end = passage.get('start'), passage.get('end')
        if (type(start) is not int or type(end) is not int
                or not 0 <= start < end <= len(report.outline.summary)
                or report.outline.summary[start:end] != passage.get('text')
                or not passage.get('sources')
                or any(source not in cards for source in passage['sources'])):
            return content
    appendix = '\n' + summary_sources_markdown(passages)
    return content[:-len(appendix)] if content.endswith(appendix) else content
