
def test_unlabeled_claim_is_not_counted_as_correct():
    from scripts.evaluate_evidence_drafts import score_claims
    result = score_claims([{'factual_correct': True, 'supported': True, 'critical': False},
                           {'factual_correct': None, 'supported': True, 'critical': True}])
    assert result['labeled_count'] == 1 and result['unlabeled_count'] == 1
    assert result['accuracy'] == 1
    assert result['critical_errors']['denominator'] == 0
    assert result['critical_errors']['rate'] is None


def test_synthetic_or_model_labels_are_not_quality_evidence():
    from scripts.evaluate_evidence_drafts import evaluate_pairs
    side = {'claims': [{'factual_correct': True, 'supported': True}], 'retrieved_source_ids':['a'], 'relevant_source_ids':['a']}
    rows = [{'case_id':'synthetic','split':'development','reviewed':False,'label_source':'synthetic','baseline':side,'proposed':side},
            {'case_id':'model','split':'held_out','reviewed':True,'label_source':'model','baseline':side,'proposed':side}]
    result = evaluate_pairs(rows)
    assert result['independently_reviewed_pairs'] == 0
    assert result['pooled']['proposed']['accuracy'] is None
    assert result['pooled']['proposed']['unlabeled_count'] == 2


def test_false_supported_recall_and_paired_delta():
    from scripts.evaluate_evidence_drafts import evaluate_pairs
    rows = [{'case_id':'c','split':'held_out','reviewed':True,'label_source':'independent_review',
             'baseline':{'claims':[{'factual_correct':False,'supported':True,'critical':True}],
                         'retrieved_source_ids':['a'],'relevant_source_ids':['a','b']},
             'proposed':{'claims':[{'factual_correct':True,'supported':True,'critical':True}],
                         'retrieved_source_ids':['a','b'],'relevant_source_ids':['a','b']}}]
    result = evaluate_pairs(rows)
    assert result['pooled']['baseline']['false_supported']['numerator'] == 1
    assert result['pairs'][0]['baseline']['retrieval_recall']['rate'] == .5
    assert result['pairs'][0]['accuracy_delta'] == 1
    assert result['pairs'][0]['proposed']['cost'] is None
