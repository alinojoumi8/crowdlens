from app.utils.model_limits import anthropic_output_settings

def test_preview_reserves_room_for_mandatory_thinking_and_final_answer():
    assert anthropic_output_settings('MiniMax-M3.1-Flash-Preview', 4096) == {'max_tokens':32768, 'output_config':{'effort':'high'}}
    assert anthropic_output_settings('MiniMax-M3.1-Flash-Preview', 40000)['max_tokens'] == 40000

def test_existing_models_preserve_the_requested_budget():
    assert anthropic_output_settings('MiniMax-M3', 4096) == {'max_tokens':4096}
