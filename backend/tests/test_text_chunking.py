"""split_text_into_chunks must always advance, whatever overlap is requested."""
import pytest

from app.utils.file_parser import split_text_into_chunks


class BoundedText(str):
    """Fails the test, instead of hanging it, when the splitter stops advancing."""

    def __new__(cls, value):
        text = super().__new__(cls, value)
        text.slices_left = 20 * len(value)
        return text

    def __getitem__(self, key):
        self.slices_left -= 1
        if self.slices_left < 0:
            raise AssertionError('split_text_into_chunks did not terminate')
        return super().__getitem__(key)


def prose(paragraphs=60):
    sentences, parts, number = [], [], 0
    for _ in range(paragraphs):
        paragraph = []
        for _ in range(6):
            number += 1
            paragraph.append(f'Sentence {number} records one more point from the council meeting.')
        sentences.extend(paragraph)
        parts.append(' '.join(paragraph) + '\n')
    return ''.join(parts), sentences


@pytest.mark.parametrize('chunk_size,overlap', [
    (500, 200), (1000, 400), (1000, 500), (500, 499), (500, 500), (300, 900),
])
def test_large_overlap_terminates_without_losing_text(chunk_size, overlap):
    text, sentences = prose()

    chunks = split_text_into_chunks(BoundedText(text), chunk_size, overlap)

    assert chunks and all(chunks)
    assert max(len(chunk) for chunk in chunks) <= chunk_size
    assert len(set(chunks)) == len(chunks)
    assert all(any(sentence in chunk for chunk in chunks) for sentence in sentences)
