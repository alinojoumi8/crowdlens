"""Normalize leaked model framing without discarding tool-call payloads."""
import re


def clean_model_text(content):
    if not isinstance(content, str):
        return ''
    content = re.sub(r'<(?:mm:)?think>.*?(?:</(?:mm:)?think>|$)', '', content,
                     flags=re.DOTALL | re.IGNORECASE)
    for token in (']<]minimax[>[', '<]minimax[>[', '[e~['):
        content = content.replace(token, '')
    return content.strip()
