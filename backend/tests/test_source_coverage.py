import pytest
from app.services.source_coverage import source_coverage


def test_each_window_is_cited_or_explicitly_excluded():
    sources = [{'evidence_id':'a'}, {'evidence_id':'b'}]
    claims = [{'citation_ids':['a']}]
    assert source_coverage(claims, [], sources)[0]['evidence_id'] == 'b'
    assert source_coverage(claims, [{'evidence_id':'b','reason':'Unrelated inventory.'}], sources) == []


@pytest.mark.parametrize('exclusions', [None, [{'evidence_id':'foreign','reason':'Unrelated'}],
    [{'evidence_id':'a','reason':'Already cited'}], [{'evidence_id':'b','reason':''}],
    [{'evidence_id':'b','reason':'Unrelated','extra':True}],
    [{'evidence_id':'b','reason':'Unrelated'}]*2])
def test_exclusions_require_unique_uncited_originals_and_bounded_reasons(exclusions):
    assert source_coverage([{'citation_ids':['a']}], exclusions, [{'evidence_id':'a'},{'evidence_id':'b'}])[0]['code'] == 'invalid_source_exclusions'
