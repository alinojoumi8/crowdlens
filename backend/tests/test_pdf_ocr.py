import io
from types import SimpleNamespace
import fitz
import pytest
from PIL import Image
from app.utils.ingestion_worker import extract_file


def mixed_pdf(tmp_path):
    path=tmp_path/'mixed.pdf'
    with fitz.open() as doc:
        page=doc.new_page();page.insert_text((50,50),'Text evidence on the first page.')
        image=Image.new('RGB',(100,100),'white');data=io.BytesIO();image.save(data,format='PNG')
        page=doc.new_page();page.insert_image(page.rect,stream=data.getvalue())
        doc.save(path)
    return str(path)


def test_mixed_pdf_retains_text_and_locally_ocr_scanned_page(tmp_path,monkeypatch):
    monkeypatch.setattr('app.utils.ingestion_worker.shutil.which',lambda name:'/usr/bin/tesseract')
    calls=[]
    def ocr(args,**kwargs):
        calls.append((args,kwargs));return SimpleNamespace(returncode=0,stdout=b'Scanned exhibit evidence')
    monkeypatch.setattr('app.utils.ingestion_worker.subprocess.run',ocr)
    text=extract_file(mixed_pdf(tmp_path))
    assert '[PDF page 1]' in text and '[PDF page 2]' in text
    assert 'Text evidence' in text and 'Scanned exhibit evidence' in text
    assert len(calls)==1 and calls[0][1]['timeout']==60
    assert calls[0][1]['input'].startswith(b'\x89PNG')


def test_missing_ocr_cannot_silently_drop_image_evidence(tmp_path,monkeypatch):
    monkeypatch.setattr('app.utils.ingestion_worker.shutil.which',lambda name:None)
    with pytest.raises(ValueError,match='PDF page 2 requires local OCR'):
        extract_file(mixed_pdf(tmp_path))


def test_failed_ocr_reports_the_page_instead_of_omitting_it(tmp_path,monkeypatch):
    monkeypatch.setattr('app.utils.ingestion_worker.shutil.which',lambda name:'/usr/bin/tesseract')
    monkeypatch.setattr('app.utils.ingestion_worker.subprocess.run',lambda *args,**kwargs:SimpleNamespace(returncode=1,stdout=b''))
    with pytest.raises(ValueError,match='Local OCR failed for PDF page 2'):
        extract_file(mixed_pdf(tmp_path))
