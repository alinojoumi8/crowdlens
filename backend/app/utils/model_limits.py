"""Output budgets for models whose mandatory thinking shares the token cap."""
def anthropic_output_settings(model, max_tokens):
    if str(model) == 'MiniMax-M3.1-Flash-Preview':
        return {'max_tokens': max(int(max_tokens), 32768), 'output_config': {'effort': 'high'}}
    return {'max_tokens': max_tokens}
