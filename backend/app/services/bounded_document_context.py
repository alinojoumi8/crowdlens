"""Sample each uploaded document without treating omitted text as absent evidence."""
import re

NOTICE = '\n[Partial source excerpts: omitted text is not absent evidence. Consult original documents before making source-coverage claims.]\n'


def document_context(text, limit):
    if len(text) <= limit:
        return text
    if limit <= len(NOTICE):
        return NOTICE[:max(0, limit)]
    sections = re.split(r'(?m)^(=== [^\n]+ ===)\s*$', text)
    if len(sections) < 3:
        return text[:limit - len(NOTICE)] + NOTICE
    documents = list(zip(sections[1::2], sections[2::2]))
    inventory = '\n'.join(header for header, _ in documents)
    room = limit - len(NOTICE) - len(inventory) - len(documents) * 2
    if room <= 0:
        return NOTICE + inventory[:limit - len(NOTICE)]
    allowance = room // len(documents)
    return NOTICE + '\n'.join(header + '\n' + body[:allowance] for header, body in documents)


def stage_context(context, limit):
    if len(context) <= limit:
        return context
    marker = '\n## Original Document Content\n'
    if limit < len(marker):
        return NOTICE[:max(0, limit)]
    prefix, found, documents = context.partition(marker)
    if not found:
        return document_context(context, limit)
    prefix = prefix[:max(0, limit // 3 - len(marker))]
    return prefix + marker + document_context(documents, limit - len(prefix) - len(marker))
