"""Bounded local retrieval over original, case-version-scoped source chunks."""
from collections import Counter
import math
import re

from .evidence_verifier import text_hash

MAX_CHUNKS = 2000
MAX_CHARS = 8_000_000
STOP = set('the a an and or in on at to for of is was were are be been by with as this that it from has have had not'.split())


def tokens(text):
    return [t for t in re.findall(r'\w+', text.casefold()) if len(t) > 1 and t not in STOP]


class SourceIndex:
    def __init__(self, episodes, scope):
        self.sources, self.counts, self.frequency = [], [], Counter()
        self.limited = len(episodes) > MAX_CHUNKS
        used = 0
        for episode in episodes[:MAX_CHUNKS]:
            if any(not scope.get(k) or episode.get(k) != scope[k] for k in ('graph_id', 'case_id', 'case_version_id')):
                continue
            text = episode.get('data')
            if not isinstance(text, str) or not text.strip() or not episode.get('document_id') or not episode.get('uuid'):
                continue
            if used + len(text) > MAX_CHARS:
                self.limited = True
                break
            used += len(text)
            self.sources.append({'evidence_id': 'episode:' + episode['uuid'], 'episode_id': episode['uuid'],
                'origin': 'source_document', 'excerpt': text, 'source_hash': text_hash(text),
                **{k: episode[k] for k in ('graph_id', 'case_id', 'case_version_id', 'document_id')},
                'filename': episode.get('filename'),
                'locator': {'page': episode.get('page'), 'paragraph': episode.get('paragraph'),
                            'chunk_index': episode.get('chunk_index'), 'char_start': 0, 'char_end': len(text),
                            'offset_basis': 'stored_chunk'}})
            count = Counter(tokens(text)); self.counts.append(count); self.frequency.update(count.keys())
        self.average = sum(sum(c.values()) for c in self.counts) / max(1, len(self.counts))
        self.digest = text_hash(str(self.limited) + '|'.join(s['evidence_id'] + s['source_hash'] for s in self.sources))

    def search(self, text, limit=4):
        query = set(tokens(text))
        ranked = []
        for i, count in enumerate(self.counts):
            score = 0.0
            for term in query & count.keys():
                idf = math.log(1 + (len(self.sources) - self.frequency[term] + .5) / (self.frequency[term] + .5))
                tf = count[term]
                score += idf * tf * 2.2 / (tf + 1.2 * (.25 + .75 * sum(count.values()) / max(1, self.average)))
            if text.strip() and text in self.sources[i]['excerpt']:
                score += 100
            # Require more than generic single-word overlap; no fabricated fallback.
            if score > 0 and len(query & count.keys()) >= min(3, max(1, len(query))):
                ranked.append((score, i))
        ranked.sort(key=lambda pair: (-pair[0], pair[1]))
        return [self.sources[i] for _, i in ranked[:limit]]


def trace_claims(claims, index):
    traced, sources = [], {}
    for claim in claims:
        candidates = index.search(claim.get('text', '')) if claim.get('text') else []
        updated = {**claim, 'association_kind': 'retrieved_candidates', 'retrieval_limited': index.limited,
                   'evidence_ids': [e['evidence_id'] for e in candidates]}
        # A fresh retrieval replaces faulty model-created associations, not prose.
        if updated.get('association_error') in {'unknown_evidence_id', 'quote_not_in_claim'}:
            updated['previous_association_error'] = updated.pop('association_error')
        traced.append(updated)
        sources.update({s['evidence_id']: s for s in candidates})
    return traced, list(sources.values())


def include_uncovered_blocks(content, claims, scope):
    """Keep unextracted prose visible instead of implying the model found every claim."""
    result = list(claims)
    for block in re.split(r"\n\s*\n", content):
        block = block.strip()
        if len(block) < 40 or block.startswith('#') or (block.startswith('**') and block.endswith('**')):
            continue
        remaining = block
        for claim in claims:
            if claim.get('text'):
                remaining = remaining.replace(claim['text'], '')
        if len(remaining.strip(' >*\n')) < 40:
            continue
        if len(result) >= 100:
            result.append({**scope, 'claim_id': 'unreviewed-remainder', 'text': '', 'kind': 'coverage_gap',
                           'evidence_ids': [], 'association_error': 'claim_budget_exceeded', 'critical': True})
            break
        result.append({**scope, 'claim_id': 'passage-' + text_hash(block)[:16], 'text': block,
                       'kind': 'unextracted_passage', 'evidence_ids': [], 'critical': True})
    return result
