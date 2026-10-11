"""Integer USD estimates, never provider billing. Policy: docs/workflow-execution.md."""
import re


def micro_usd(value, *, positive=False):
    # Decimal strings avoid binary float rounding and silent fractional truncation.
    if not isinstance(value, str) or not re.fullmatch(r'(0|[1-9][0-9]{0,6})(\.[0-9]{1,6})?', value):
        raise ValueError('invalid_usd_decimal')
    whole, _, fraction = value.partition('.')
    amount = int(whole) * 1_000_000 + int(fraction.ljust(6, '0') or '0')
    if amount > 1_000_000_000_000 or (positive and amount == 0):
        raise ValueError('invalid_usd_amount')
    return amount


def price_terms(value):
    if not isinstance(value, dict) or set(value) != {
        'currency', 'budget_usd', 'reserve_usd', 'input_usd_per_million',
        'output_usd_per_million', 'price_reference',
    } or value.get('currency') != 'USD':
        raise ValueError('invalid_spend_terms')
    reference = value['price_reference']
    if not isinstance(reference, str) or not 1 <= len(reference.strip()) <= 500:
        raise ValueError('price_reference_required')
    terms = dict(currency='USD', policy_version=1, price_reference=reference.strip(),
                 budget_micro_usd=micro_usd(value['budget_usd'], positive=True),
                 reserve_micro_usd=micro_usd(value['reserve_usd'], positive=True),
                 input_rate_micro_usd=micro_usd(value['input_usd_per_million']),
                 output_rate_micro_usd=micro_usd(value['output_usd_per_million']))
    if terms['reserve_micro_usd'] > terms['budget_micro_usd']:
        raise ValueError('reservation_exceeds_budget')
    return terms


def token_counts(usage):
    if not isinstance(usage, dict):
        return None
    def valid(value):
        return type(value) is int and 0 <= value <= 1_000_000_000
    if all(valid(usage.get(k)) for k in ('input_tokens', 'output_tokens')):
        # Anthropic input_tokens excludes cache writes/reads. Apply the supplied
        # input rate to all input tokens; operators must include any cache premium.
        caches = [usage.get(k, 0) for k in ('cache_creation_input_tokens', 'cache_read_input_tokens')]
        if not all(valid(n) for n in caches):
            return None
        return usage['input_tokens'] + sum(caches), usage['output_tokens']
    if all(valid(usage.get(k)) for k in ('prompt_tokens', 'completion_tokens')):
        # OpenAI prompt_tokens already includes cached tokens; completion_tokens
        # includes reasoning. Do not add the detail fields a second time.
        return usage['prompt_tokens'], usage['completion_tokens']
    return None


def estimated_micro_usd(usage, terms):
    counts = token_counts(usage)
    if counts is None:
        return None
    numerator = counts[0] * terms['input_rate_micro_usd'] + counts[1] * terms['output_rate_micro_usd']
    return (numerator + 999_999) // 1_000_000  # Always round up to one microdollar.
