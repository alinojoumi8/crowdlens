import pytest


def test_budget_monotonic_and_usage_unknown():
    from app.utils.draft_budget import DraftBudget, DeadlineExceeded
    now = [10.0]
    budget = DraftBudget(clock=lambda: now[0])
    now[0] = 189.5
    assert budget.remaining() == pytest.approx(.5)
    budget.record_usage('fake', 'model', {'input_tokens': 3}, 10)
    assert budget.snapshot()['calls'][0]['output_tokens'] is None
    now[0] = 190
    with pytest.raises(DeadlineExceeded):
        budget.check()
