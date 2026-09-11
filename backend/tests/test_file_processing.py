import io
import docx
import pymupdf as fitz
from fastapi.testclient import TestClient
from app.main import app
from app.services.file_processing_service import (
    process_uploaded_file,
    extract_from_txt,
    extract_from_pdf,
    extract_from_docx,
    EmptyFileError,
    UnsupportedFileTypeError,
    FileOversizedError,
    NoSelectableTextPDFError,
)

client = TestClient(app)

SAMPLE_CHAT_TXT = """[10/12/2024, 08:34] David Miller: Morning team. Let's reduce reception desk width by 300 mm.
[10/12/2024, 08:42] Elena Vance: Understood. I will issue revised drawings by Friday.
[10/12/2024, 08:49] Marcus Brody: We need the drawings before starting ceiling framing.
"""


def create_sample_pdf(pages_text: list) -> bytes:
    """Creates an in-memory PDF with the provided page texts."""
    doc = fitz.open()
    for text in pages_text:
        page = doc.new_page()
        if text:
            page.insert_text((50, 50), text, fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_sample_docx(paragraphs: list) -> bytes:
    """Creates an in-memory DOCX with the provided paragraphs."""
    doc = docx.Document()
    for p_text in paragraphs:
        doc.add_paragraph(p_text)
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()


def test_txt_extraction():
    res = extract_from_txt(SAMPLE_CHAT_TXT.encode("utf-8"), "chat_log.txt")
    assert res.filename == "chat_log.txt"
    assert res.source_type == "Chat Export"
    assert len(res.blocks) == 3
    assert res.blocks[0].location == "Message #1"
    assert res.blocks[0].sender == "David Miller"
    assert "300 mm" in res.blocks[0].text


def test_pdf_extraction_with_pages():
    pages = [
        "Page 1 content: Client requested desk reduction.\nArchitect agreed.",
        "Page 2 content: Ceiling framing deadline is set for Friday.",
    ]
    pdf_bytes = create_sample_pdf(pages)
    res = extract_from_pdf(pdf_bytes, "project_notes.pdf")
    assert res.filename == "project_notes.pdf"
    assert res.source_type == "Document"
    # Check that locations track page numbers
    locations = [b.location for b in res.blocks]
    assert any("Page 1" in loc for loc in locations)
    assert any("Page 2" in loc for loc in locations)


def test_docx_extraction_with_paragraphs():
    paras = [
        "Project Update Header",
        "The lobby layout has been approved by the client.",
        "Contractor will mobilize scaffolding on October 24th.",
    ]
    docx_bytes = create_sample_docx(paras)
    res = extract_from_docx(docx_bytes, "memo.docx")
    assert res.filename == "memo.docx"
    assert len(res.blocks) == 3
    assert "Paragraph 1" in res.blocks[0].location
    assert "Paragraph 2" in res.blocks[1].location


def test_empty_file_validation():
    # Empty TXT
    try:
        process_uploaded_file(b"", "empty.txt")
        assert False, "Should have raised EmptyFileError"
    except EmptyFileError:
        pass

    # Empty file via API endpoint
    response = client.post(
        "/api/analyze/file",
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_unsupported_extension():
    try:
        process_uploaded_file(b"some binary content", "malicious.exe")
        assert False, "Should have raised UnsupportedFileTypeError"
    except UnsupportedFileTypeError:
        pass

    response = client.post(
        "/api/analyze/file",
        files={"file": ("program.exe", b"binary data", "application/octet-stream")},
    )
    assert response.status_code == 415
    assert "Unsupported file format" in response.json()["detail"]


def test_oversized_file():
    from app.services.file_processing_service import MAX_FILE_SIZE_BYTES
    oversized_bytes = b"a" * (MAX_FILE_SIZE_BYTES + 10)
    try:
        process_uploaded_file(oversized_bytes, "huge.txt")
        assert False, "Should have raised FileOversizedError"
    except FileOversizedError:
        pass


def test_scanned_empty_pdf_detection():
    # Create PDF with 2 pages of 0 text
    blank_pdf = create_sample_pdf(["", ""])
    try:
        extract_from_pdf(blank_pdf, "scanned_doc.pdf")
        assert False, "Should have raised NoSelectableTextPDFError"
    except NoSelectableTextPDFError as e:
        assert "This PDF does not contain selectable text" in str(e)

    # Via API endpoint
    response = client.post(
        "/api/analyze/file",
        files={"file": ("scanned.pdf", blank_pdf, "application/pdf")},
    )
    assert response.status_code == 400
    assert "Scanned PDF/OCR support is not available yet" in response.json()["detail"]


def test_file_api_endpoint_integration():
    # Test valid text file upload through the API endpoint
    response = client.post(
        "/api/analyze/file",
        files={"file": ("site_notes.txt", SAMPLE_CHAT_TXT.encode("utf-8"), "text/plain")},
    )
    # If GEMINI_API_KEY is set, should return 200 with ShiftlyAnalysisResult
    # If not set, returns 503
    assert response.status_code in [200, 503]
    if response.status_code == 200:
        data = response.json()
        assert "keyPoints" in data
        assert "actions" in data
        assert "summary" in data


def test_existing_paste_analyze_regression():
    # Ensure existing POST /api/analyze still works
    res = client.post("/api/analyze", json={"text": SAMPLE_CHAT_TXT})
    assert res.status_code in [200, 503]


def test_txt_encodings_windows_notepad():
    sample = "Client: We reviewed the latest design package. Reception desk width reduced by 300 mm.\nArchitect: Revised drawings by Friday, September 11.\n"
    # 1. UTF-8
    res_utf8 = extract_from_txt(sample.encode("utf-8"), "notepad_utf8.txt")
    assert "300 mm" in res_utf8.full_text
    assert len(res_utf8.blocks) == 2

    # 2. UTF-8 BOM
    res_bom = extract_from_txt(sample.encode("utf-8-sig"), "notepad_utf8_bom.txt")
    assert "300 mm" in res_bom.full_text
    assert len(res_bom.blocks) == 2

    # 3. UTF-16 LE
    res_utf16le = extract_from_txt(sample.encode("utf-16-le"), "notepad_utf16_le.txt")
    assert "300 mm" in res_utf16le.full_text
    assert len(res_utf16le.blocks) == 2

    # 4. UTF-16 BE
    res_utf16be = extract_from_txt(sample.encode("utf-16-be"), "notepad_utf16_be.txt")
    assert "300 mm" in res_utf16be.full_text
    assert len(res_utf16be.blocks) == 2

    # 5. UTF-16 with BOM (Standard Windows Notepad default)
    res_utf16 = extract_from_txt(sample.encode("utf-16"), "notepad_utf16_bom.txt")
    assert "300 mm" in res_utf16.full_text
    assert len(res_utf16.blocks) == 2


if __name__ == "__main__":
    test_txt_extraction()
    test_txt_encodings_windows_notepad()
    test_pdf_extraction_with_pages()
    test_docx_extraction_with_paragraphs()
    test_empty_file_validation()
    test_unsupported_extension()
    test_oversized_file()
    test_scanned_empty_pdf_detection()
    test_file_api_endpoint_integration()
    test_existing_paste_analyze_regression()
    print("All Step 3 file processing tests passed successfully!")

