"""Versioned, separately persisted human judgments on immutable proposal content."""
from contextlib import contextmanager
import copy
import hashlib
import io
import json
import os
import sqlite3
import zipfile

from .human_review_validation import assess_reviews, json_bytes
from .proposal_store import ProposalError, now, proposal_digest


def packet_for(record):
    from .workspace import require
    require("proposal", record.get("proposal_id"))
    require("report", record.get("parent_report_id"))
    if record.get('state') in {'queued', 'running'} or not record.get('ledger') or not record.get('proposal_digest'):
        raise ProposalError('review_packet_unavailable')
    if proposal_digest(record) != record['proposal_digest']:
        raise ProposalError('review_content_changed')
    claims = [{key: copy.deepcopy(claim.get(key)) for key in
               ('claim_id', 'kind', 'text', 'attribution', 'premise_claim_ids', 'citation_ids')}
              for claim in record['ledger']]
    ids = [claim['claim_id'] for claim in claims]
    if any(not isinstance(i, str) or not i for i in ids) or len(ids) != len(set(ids)):
        raise ProposalError('invalid_claim_ledger')
    sources = [{**copy.deepcopy(source), 'source_id': source['evidence_id'],
                'excerpt': source.get('window', ''), 'source_sha256': source.get('source_hash')}
               for source in record.get('sources', [])]
    packet = dict(schema_version=1, packet_id='packet_' + record['proposal_id'],
                  notice='Review this frozen proposal against its retained original excerpts. These ratings do not approve or change the report.',
                  report_id=record['parent_report_id'], proposal_id=record['proposal_id'],
                  proposal_digest=record['proposal_digest'], scope=record.get('scope'),
                  section_index=record.get('section_index'), sources=sources, claims=claims,
                  candidate_section=record.get('after', {}).get('section'),
                  candidate_summary=record.get('after', {}).get('summary'))
    return packet, hashlib.sha256(json_bytes(packet)).hexdigest()


def blank_form(packet, digest):
    return dict(schema_version=1, packet_id=packet['packet_id'], packet_sha256=digest,
                reviewer_id=None, reviewer_kind=None, reviewed_at=None, review_seconds=None,
                claims=[dict(claim_id=c['claim_id'], support=None, attribution_correct=None,
                             citation_support_correct=None, rationale=None) for c in packet['claims']],
                reference_facts=None, omitted_reference_fact_ids=None, conflicts_handled=None, notes=None)


class HumanReviewStore:
    def __init__(self, proposal_store):
        self.proposals = proposal_store

    @contextmanager
    def connection(self):
        path = self.proposals.path('.human-reviews.sqlite3')
        for suffix in ('-wal', '-shm', '-journal'):
            self.proposals.path(path.name + suffix)
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        except FileExistsError:
            pass
        else:
            os.close(fd)
        db = sqlite3.connect(path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('PRAGMA synchronous=FULL')
            db.execute('CREATE TABLE IF NOT EXISTS packets (digest TEXT PRIMARY KEY, content BLOB NOT NULL)')
            db.execute('''CREATE TABLE IF NOT EXISTS reviews (
                packet_digest TEXT NOT NULL, reviewer_id TEXT NOT NULL, version INTEGER NOT NULL,
                form_json TEXT NOT NULL, PRIMARY KEY (packet_digest, reviewer_id, version))''')
            db.commit()
            yield db
        finally:
            db.close()

    def _snapshot(self, record):
        packet, digest = packet_for(record)
        with self.connection() as db:
            history = [dict(reviewer_id=r['reviewer_id'], version=r['version'], form=json.loads(r['form_json']))
                       for r in db.execute('SELECT * FROM reviews WHERE packet_digest=? ORDER BY reviewer_id,version', (digest,))]
        # A single SELECT gives the UI and export one consistent read snapshot,
        # including when another reviewer saves during bundle construction.
        latest = {row['reviewer_id']: row for row in history}
        current = [dict(version=row['version'], form=row['form']) for row in latest.values()]
        assessment = assess_reviews({packet['packet_id']: (packet, digest)}, [row['form'] for row in current])
        result = dict(packet=packet, packet_sha256=digest, blank_form=blank_form(packet, digest),
                    reviews=current, assessment=assessment,
                    history=[dict(reviewer_id=r['reviewer_id'], version=r['version'],
                                  reviewed_at=r['form']['reviewed_at']) for r in history])
        return result, history

    def view(self, record):
        return self._snapshot(record)[0]

    def save(self, record, form, expected_version):
        packet, digest = packet_for(record)
        if type(expected_version) is not int or expected_version < 0:
            raise ProposalError('invalid_review_version', 400)
        if not isinstance(form, dict) or set(form) != set(blank_form(packet, digest)):
            raise ProposalError('invalid_review_schema', 400)
        if form.get('packet_sha256') != digest:
            raise ProposalError('review_content_changed')
        if not isinstance(form.get('reviewer_id'), str) or not 1 <= len(form['reviewer_id'].strip()) <= 120:
            raise ProposalError('reviewer_identity_required', 400)
        if form.get('reviewer_kind') not in {'human', 'expert_human'}:
            raise ProposalError('human_provenance_required', 400)
        form = copy.deepcopy(form)
        if form.get('notes') is not None and not isinstance(form['notes'], str):
            raise ProposalError('invalid_review_notes', 400)
        form['reviewer_id'] = form['reviewer_id'].strip()
        form['reviewed_at'] = now()
        try:
            assess_reviews({packet['packet_id']: (packet, digest)}, [form])
            encoded = json_bytes(form)
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            raise ProposalError(str(exc) if isinstance(exc, ValueError) else 'invalid_review_schema', 400) from exc
        if len(encoded) > 256 * 1024:
            raise ProposalError('review_too_large', 400)
        with self.connection() as db, db:
            db.execute('BEGIN IMMEDIATE')
            version = db.execute('SELECT COALESCE(MAX(version),0) FROM reviews WHERE packet_digest=? AND reviewer_id=?',
                                 (digest, form['reviewer_id'])).fetchone()[0]
            if version != expected_version:
                raise ProposalError('review_version_conflict')
            db.execute('INSERT OR IGNORE INTO packets VALUES (?,?)', (digest, json_bytes(packet)))
            stored = db.execute('SELECT content FROM packets WHERE digest=?', (digest,)).fetchone()[0]
            if bytes(stored) != json_bytes(packet):
                raise ProposalError('review_content_changed')
            db.execute('INSERT INTO reviews VALUES (?,?,?,?)', (digest, form['reviewer_id'], version + 1, encoded.decode()))
        return self.view(record)

    def export(self, record):
        result, history = self._snapshot(record)
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w', zipfile.ZIP_DEFLATED) as bundle:
            bundle.writestr('reviewer/' + result['packet']['packet_id'] + '.json', json_bytes(result['packet']))
            forms = [row['form'] for row in result['reviews']] or [result['blank_form']]
            bundle.writestr('reviews.jsonl', ''.join(json.dumps(form, ensure_ascii=False, allow_nan=False) + '\n' for form in forms))
            bundle.writestr('history.json', json_bytes(history))
            bundle.writestr('assessment.json', json_bytes(result['assessment']))
            bundle.writestr('README.txt', 'Frozen application review packet, not a blinded benchmark.\n'
                            'Reviewers are self-identified local operators; identity is not authenticated.\n'
                            'Latest forms: reviews.jsonl. Prior saved versions: history.json.\n'
                            'From the repository: python backend/scripts/score_evidence_quality_reviews.py '
                            '--packets PATH/reviewer --reviews PATH/reviews.jsonl --output NEW_OUTPUT.json\n')
        data.seek(0)
        return data
