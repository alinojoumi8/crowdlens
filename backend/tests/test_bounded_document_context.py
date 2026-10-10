from app.services.bounded_document_context import document_context, stage_context


def test_later_document_retained_under_stage_budget():
    documents = '=== defendant.pdf ===\nSet aside requested.\n' + 'background ' * 4000 + '\n=== plaintiff.pdf ===\nProduction requested; allegations disputed.\n' + 'reply ' * 4000
    context = '## Simulation Requirements\nCompare attributed positions.\n' + '\n## Original Document Content\n' + documents
    for limit in (8000, 10000):
        result = stage_context(context, limit)
        assert len(result) <= limit
        assert 'Compare attributed positions.' in result
        assert '=== defendant.pdf ===' in result and 'Set aside requested.' in result
        assert '=== plaintiff.pdf ===' in result and 'Production requested; allegations disputed.' in result
        assert 'omitted text is not absent evidence' in result


def test_small_complete_input_unchanged():
    text = '=== a.pdf ===\nNo admission.\n=== b.pdf ===\nOnly if testing is supplied.'
    assert document_context(text, 1000) == text
    assert stage_context(text, 1000) == text


def test_tiny_budget_and_unmarked_source_are_bounded():
    for limit in (0, 10, 150, 300):
        for text in ('ordinary source ' * 100, '=== ' + 'a' * 500 + ' ===\nbody\n=== b.pdf ===\nnext'):
            assert len(document_context(text, limit)) <= limit
            assert len(stage_context('prefix' * 100 + '\n## Original Document Content\n' + text, limit)) <= limit


def test_both_generation_stages_receive_later_source():
    from app.services.simulation_config_generator import SimulationConfigGenerator
    generator = object.__new__(SimulationConfigGenerator)
    prompts = []
    generator._call_llm_with_retry = lambda prompt, system: prompts.append(prompt) or {}
    context = 'Requirements\n## Original Document Content\n=== first.pdf ===\n' + 'first ' * 9000 + '\n=== later.pdf ===\nLater party requests production.'
    generator._generate_time_config(context, 6, {})
    generator._generate_event_config(context, 'Compare both sides', [], {})
    assert len(prompts) == 2
    assert all('later.pdf' in prompt and 'Later party requests production.' in prompt for prompt in prompts)
