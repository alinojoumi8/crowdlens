"""Human review does not generate content or alter sealed proposal artifacts."""
from flask import jsonify, request, send_file

from . import report_bp
from .evidence_proposals import endpoint, store_for_app
from ..services.human_reviews import HumanReviewStore
from ..services.proposal_store import ProposalError


@report_bp.route('/<report_id>/evidence-proposals/<proposal_id>/human-reviews', methods=['GET', 'POST'])
@endpoint
def human_reviews(report_id, proposal_id):
    proposals = store_for_app()
    record = proposals.get(report_id, proposal_id)
    store = HumanReviewStore(proposals)
    if request.method == 'GET':
        return jsonify(success=True, data=store.view(record))
    request.max_content_length = 256 * 1024
    body = request.get_json()
    if not isinstance(body, dict) or set(body) != {'form', 'expected_version'}:
        raise ProposalError('invalid_request', 400)
    return jsonify(success=True, data=store.save(record, body['form'], body['expected_version']))


@report_bp.route('/<report_id>/evidence-proposals/<proposal_id>/human-reviews/export', methods=['GET'])
@endpoint
def export_human_reviews(report_id, proposal_id):
    proposals = store_for_app()
    record = proposals.get(report_id, proposal_id)
    return send_file(HumanReviewStore(proposals).export(record), mimetype='application/zip',
                     as_attachment=True, download_name='review-' + proposal_id + '.zip', max_age=0)
