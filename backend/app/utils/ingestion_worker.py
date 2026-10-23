"""Disposable parser process. No app startup, credentials, model or graph clients."""
import json
import math
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys

if __package__:
    from .ingestion_limits import (MAX_FILE_BYTES, MAX_TEXT_CHARS, MAX_PDF_PAGES,
        MAX_PAGE_PIXELS, MAX_OCR_PAGES, WORKER_CPU_SECONDS, WORKER_MEMORY_BYTES)
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from ingestion_limits import (MAX_FILE_BYTES, MAX_TEXT_CHARS, MAX_PDF_PAGES,
        MAX_PAGE_PIXELS, MAX_OCR_PAGES, WORKER_CPU_SECONDS, WORKER_MEMORY_BYTES)


def text_bytes(data, encoding=None):
    if not data or len(data) > MAX_FILE_BYTES:
        raise ValueError('File is empty or exceeds the 50 MiB file limit.')
    # Text formats have no magic signature: reject known binary signatures and
    # decoded control bytes; retain Unicode/BOM and legacy text encodings.
    if data.startswith((b'MZ', b'\x7fELF', b'PK\x03\x04', b'%PDF-', b'\x89PNG', b'\xff\xd8\xff', b'GIF8')):
        raise ValueError('Binary content does not match the text file type.')
    if encoding:
        try:
            text = data.decode(encoding, errors='strict')
        except (LookupError, UnicodeError):
            return text_bytes(data)
    elif data.startswith((b'\xff\xfe', b'\xfe\xff')):
        text = data.decode('utf-16')
    else:
        try:
            text = data.decode('utf-8-sig')
        except UnicodeDecodeError:
            from charset_normalizer import from_bytes
            best = from_bytes(data).best()
            if best is None:
                raise ValueError('Text encoding could not be validated.')
            text = str(best)
    if any(ord(c) < 32 and c not in '\t\r\n\f' for c in text):
        raise ValueError('Binary control bytes are not permitted in text files.')
    if len(text) > MAX_TEXT_CHARS:
        raise ValueError('Extracted text exceeds the character limit; split the source and retry.')
    return text


def extract_pdf_bytes(data):
    import fitz
    if not data.startswith(b'%PDF-') or len(data) > MAX_FILE_BYTES:
        raise ValueError('File signature does not match PDF or exceeds the file limit.')
    parts, count = [], 0
    with fitz.open(stream=data, filetype='pdf') as doc:
        if doc.needs_pass or not 0 < doc.page_count <= MAX_PDF_PAGES:
            raise ValueError('Encrypted, empty or over-limit PDF is not supported; split the source and retry.')
        # Preflight all pages before spending any OCR time. A small explicit
        # scan envelope fits the fixed worker budget without promising bulk OCR.
        pages, scan_count, text_count = [], 0, 0
        for page in doc:
            text = page.get_text()
            needs_ocr = len(text.strip()) < 20 and bool(page.get_images())
            scan_count += bool(needs_ocr)
            text_count += len(text)
            if scan_count > MAX_OCR_PAGES:
                raise ValueError(f'At most {MAX_OCR_PAGES} scanned PDF page per source is supported; split the source and retry.')
            if text_count > MAX_TEXT_CHARS:
                raise ValueError('Extracted text exceeds the character limit; split the source and retry.')
            pages.append((text, needs_ocr))
        # PDF actions/attachments are never executed or returned to a browser.
        for number, (text, needs_ocr) in enumerate(pages, 1):
            if needs_ocr:
                page = doc[number - 1]
                pixels = math.ceil(page.rect.width * 2.5) * math.ceil(page.rect.height * 2.5)
                if not 0 < pixels <= MAX_PAGE_PIXELS:
                    raise ValueError(f'PDF page {number} exceeds the OCR pixel limit.')
                executable = shutil.which('tesseract')
                if not executable:
                    raise ValueError(f'PDF page {number} requires local OCR. Install Tesseract before retrying; scanned pages cannot be silently skipped.')
                result = subprocess.run([executable, 'stdin', 'stdout', '-l', 'eng', '--psm', '3'],
                    input=page.get_pixmap(dpi=180).tobytes('png'), stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL, timeout=60, check=False)
                if result.returncode:
                    raise ValueError(f'Local OCR failed for PDF page {number}; retry after checking Tesseract.')
                text = result.stdout.decode('utf-8', errors='strict')
            if text.strip():
                part = f'[PDF page {number}]\n{text}'
                count += len(part) + 2
                if count > MAX_TEXT_CHARS:
                    raise ValueError('Extracted text exceeds the character limit; split the source and retry.')
                parts.append(part)
    return '\n\n'.join(parts)


def extract_file(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= MAX_FILE_BYTES:
        raise ValueError('Invalid, empty or over-limit source file.')
    data = path.read_bytes()
    if path.suffix.lower() == '.pdf':
        return extract_pdf_bytes(data)
    if path.suffix.lower() not in {'.txt', '.md', '.markdown'}:
        raise ValueError('Unsupported file format.')
    return text_bytes(data)


def main():
    # Limits apply before importing native parsers. OCR inherits them and the
    # process group; the parent kills/reaps the entire group on wall timeout.
    resource.setrlimit(resource.RLIMIT_AS, (WORKER_MEMORY_BYTES, WORKER_MEMORY_BYTES))
    resource.setrlimit(resource.RLIMIT_CPU, (WORKER_CPU_SECONDS, WORKER_CPU_SECONDS))
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_TEXT_CHARS * 12 + 4096, MAX_TEXT_CHARS * 12 + 4096))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    os.umask(0o077)
    try:
        mode, value = json.loads(sys.stdin.read(16384))
        if mode == 'file':
            result = extract_file(value)
        elif mode == 'url':
            import url_fetcher
            url_fetcher._extract_pdf_bytes = extract_pdf_bytes
            result = url_fetcher._fetch_url(value)
        else:
            raise ValueError('Unsupported ingestion operation.')
        print(json.dumps({'result': result}, ensure_ascii=True))
    except ValueError as exc:
        print(json.dumps({'error': str(exc)[:500]}))
    except Exception:
        # Parser paths, payloads and native diagnostics stay out of API errors.
        print(json.dumps({'error': 'Source could not be safely extracted; check its type and limits.'}))


if __name__ == '__main__':
    main()
