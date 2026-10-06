"""Exact page boundaries in the locally extracted, marker-bearing PDF text.

A terminal page without its next marker is not known complete in a stored chunk.
Page completeness describes extraction boundaries, not semantic completeness.
"""
import re


def complete_pages(text):
    markers = list(re.finditer(r'(?m)^\[PDF page ([1-9][0-9]*)\]\s*\n', text))
    return [(int(left.group(1)), left.start(), right.start())
            for left, right in zip(markers, markers[1:])
            if int(right.group(1)) == int(left.group(1)) + 1]


def page_window(text, anchor, maximum=4000):
    for page, start, end in complete_pages(text):
        if start <= anchor < end and end - start <= maximum:
            return page, start, end
    return None


def exact_extract_range(source):
    """Full legacy excerpt or complete page, never a punctuation-based slice."""
    text = source['excerpt']
    start, end = len(text) - len(text.lstrip()), len(text.rstrip())
    if end - start <= 4000 and source['window_start'] <= start < end <= source['window_end']:
        return start, end
    for _, start, end in complete_pages(text):
        trimmed_end = len(text[:end].rstrip())
        if (source['window_start'] == start and source['window_end'] == end
                and 0 < trimmed_end - start <= 4000):
            return start, trimmed_end
    return None
