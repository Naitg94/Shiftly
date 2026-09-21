import io
import os
import zipfile
import email
from email.message import EmailMessage
from fastapi.testclient import TestClient
from app.main import app
from app.services.file_processing_service import (
    process_uploaded_file,
    extract_from_whatsapp_zip,
    extract_from_eml,
    extract_from_mbox,
    InvalidWhatsAppZipError,
    ZipSecurityError,
    ZipBombError,
    EmailParsingError,
    EmptyFileError,
    MAX_ZIP_ENTRIES,
    MAX_ZIP_UNCOMPRESSED_BYTES,
)

import os
import pytest
from unittest.mock import patch
from app.core.rate_limiter import rate_limiter
from app.core.config import settings

os.environ["TEST_USE_SQLITE"] = "true"

auth_client = TestClient(app, headers={"Authorization": "Bearer test-token-123"})
guest_client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_limiter():
    rate_limiter.reset()
    with patch.object(settings, "PRIVATE_PRO_USER_IDS_RAW", "00000000-0000-0000-0000-000000000001"):
        yield
    rate_limiter.reset()


def build_zip_archive(files_dict: dict) -> bytes:
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for arcname, data in files_dict.items():
            if isinstance(data, str):
                zf.writestr(arcname, data.encode("utf-8"))
            else:
                zf.writestr(arcname, data)
    return bio.getvalue()


def test_whatsapp_zip_ios_format():
    chat_content = (
        "[24/05/2024, 09:30:15] Alice Morgan: Kickoff meeting is confirmed for 10 AM.\n"
        "[24/05/2024, 09:31:02] Bob Vance: I will prepare the architectural blueprints.\n"
        "[24/05/2024, 09:35:40] Charlie Green: We must finalize the electrical load sign-off by Friday.\n"
    )
    zip_bytes = build_zip_archive({"_chat.txt": chat_content})
    res = extract_from_whatsapp_zip(zip_bytes, "WhatsApp Chat with Team.zip")
    
    assert res.source_type == "Chat Export"
    assert len(res.blocks) == 3
    assert res.blocks[0].sender == "Alice Morgan"
    assert "Message #1" in res.blocks[0].location
    assert "Kickoff meeting" in res.blocks[0].text
    assert res.blocks[1].sender == "Bob Vance"
    assert res.blocks[2].sender == "Charlie Green"
    assert "finalize the electrical load" in res.full_text


def test_whatsapp_zip_android_format():
    chat_content = (
        "24/05/24, 14:15 - Alice Morgan: Please review the updated scope document.\n"
        "24/05/24, 14:20 - Bob Vance: Reviewed and approved the layout.\n"
    )
    zip_bytes = build_zip_archive({"_chat.txt": chat_content})
    res = extract_from_whatsapp_zip(zip_bytes, "WhatsApp Android Chat.zip")
    
    assert res.source_type == "Chat Export"
    assert len(res.blocks) == 2
    assert res.blocks[0].sender == "Alice Morgan"
    assert res.blocks[1].sender == "Bob Vance"
    assert "Reviewed and approved" in res.blocks[1].text


def test_whatsapp_zip_multiline_messages():
    chat_content = (
        "[24/05/2024, 11:00:00] Alice Morgan: Action items for this week:\n"
        "1. Inspect foundation stability.\n"
        "2. Confirm concrete pouring window.\n"
        "3. Submit structural sign-off to city council.\n"
        "[24/05/2024, 11:05:00] Bob Vance: Understood, I am on it.\n"
    )
    zip_bytes = build_zip_archive({"_chat.txt": chat_content})
    res = extract_from_whatsapp_zip(zip_bytes, "WhatsApp Multiline.zip")
    
    assert len(res.blocks) == 2
    assert res.blocks[0].sender == "Alice Morgan"
    assert "Inspect foundation stability" in res.blocks[0].text
    assert "Submit structural sign-off" in res.blocks[0].text
    assert res.blocks[1].sender == "Bob Vance"


def test_whatsapp_zip_unicode_hinglish_emoji():
    chat_content = (
        "[24/05/2024, 12:00:00] Rahul Sharma: Haan bilkul 👍 Milestone 1 deadline is Monday!\n"
        "[24/05/2024, 12:01:10] Priya Patel: Bahut badhiya 🎉 drawings are ready for dispatch.\n"
    )
    zip_bytes = build_zip_archive({"_chat.txt": chat_content})
    res = extract_from_whatsapp_zip(zip_bytes, "WhatsApp Hinglish.zip")
    
    assert len(res.blocks) == 2
    assert "👍" in res.blocks[0].text
    assert "Rahul Sharma" == res.blocks[0].sender
    assert "Priya Patel" == res.blocks[1].sender
    assert "drawings are ready" in res.blocks[1].text


def test_whatsapp_zip_ignores_media_binaries():
    chat_content = (
        "[24/05/2024, 10:00:00] Alice Morgan: Here is the ceiling detail.\n"
        "[24/05/2024, 10:00:05] Alice Morgan: <Media omitted>\n"
        "[24/05/2024, 10:01:00] Bob Vance: Received photo.\n"
    )
    zip_bytes = build_zip_archive({
        "_chat.txt": chat_content,
        "IMG-20240524-WA0001.jpg": b"\xff\xd8\xff\xe0" + b"0" * 5000,
        "VID-20240524-WA0002.mp4": b"\x00\x00\x00 ftyp" + b"1" * 10000,
        "PTT-20240524-WA0003.opus": b"OpusHead" + b"2" * 4000,
        "specs.pdf": b"%PDF-1.4 dummy binary specifications",
    })
    res = extract_from_whatsapp_zip(zip_bytes, "WhatsApp with Media.zip")
    
    assert res.source_type == "Chat Export"
    assert "Alice Morgan" in res.full_text
    assert "Bob Vance" in res.full_text
    assert "OpusHead" not in res.full_text
    assert "%PDF-1.4" not in res.full_text


def test_whatsapp_zip_subfolder_location():
    chat_content = "[24/05/2024, 08:00:00] Sarah: Good morning team, let us begin.\n"
    zip_bytes = build_zip_archive({"ExportFolder/_chat.txt": chat_content})
    res = extract_from_whatsapp_zip(zip_bytes, "Nested WhatsApp.zip")
    assert len(res.blocks) == 1
    assert res.blocks[0].sender == "Sarah"


def test_whatsapp_zip_missing_chat_txt_rejected():
    zip_bytes = build_zip_archive({
        "random_image.jpg": b"image_bytes",
        "document.pdf": b"%PDF-1.4 dummy",
    })
    try:
        extract_from_whatsapp_zip(zip_bytes, "invalid.zip")
        assert False, "Should have raised InvalidWhatsAppZipError"
    except InvalidWhatsAppZipError as e:
        assert "_chat.txt" in str(e)

    # Verify HTTP endpoint returns 400
    resp = auth_client.post(
        "/api/analyze/file",
        files={"file": ("invalid.zip", zip_bytes, "application/zip")}
    )
    assert resp.status_code == 400


def test_whatsapp_zip_corrupt_bytes_rejected():
    corrupted_bytes = b"PK\x03\x04corrupted_header_data"
    response = auth_client.post(
        "/api/analyze/file",
        files={"file": ("corrupt.zip", corrupted_bytes, "application/zip")}
    )
    assert response.status_code in (400, 415)


def test_zip_path_traversal_rejected():
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w") as zf:
        zf.writestr("../../evil.txt", "malicious path traversal content")
        zf.writestr("_chat.txt", "[24/05/2024, 10:00:00] Alice: Valid line.\n")
    zip_bytes = bio.getvalue()
    
    try:
        extract_from_whatsapp_zip(zip_bytes, "slip.zip")
        assert False, "Should have raised ZipSecurityError"
    except ZipSecurityError as e:
        assert "traversal" in str(e).lower()

    # Verify HTTP endpoint returns 400 Bad Request
    resp = auth_client.post(
        "/api/analyze/file",
        files={"file": ("slip.zip", zip_bytes, "application/zip")}
    )
    assert resp.status_code == 400


def test_zip_excessive_entries_rejected():
    files = {f"file_{i}.txt": f"content {i}" for i in range(MAX_ZIP_ENTRIES + 5)}
    files["_chat.txt"] = "[24/05/2024, 10:00:00] Alice: Hello"
    zip_bytes = build_zip_archive(files)
    
    try:
        extract_from_whatsapp_zip(zip_bytes, "many_entries.zip")
        assert False, "Should have raised ZipBombError"
    except ZipBombError as e:
        assert "entries" in str(e).lower()

    # Verify HTTP endpoint returns 413 Payload Too Large
    resp = auth_client.post(
        "/api/analyze/file",
        files={"file": ("many_entries.zip", zip_bytes, "application/zip")}
    )
    assert resp.status_code == 413
    assert "entries" in resp.json()["detail"].lower()


def test_zip_uncompressed_size_limit_rejected(monkeypatch):
    import app.services.file_processing_service as fps
    monkeypatch.setattr(fps, "MAX_ZIP_UNCOMPRESSED_BYTES", 500)
    zip_bytes = build_zip_archive({"_chat.txt": "A" * 1000})

    try:
        extract_from_whatsapp_zip(zip_bytes, "huge_uncompressed.zip")
        assert False, "Should have raised ZipBombError"
    except ZipBombError as e:
        assert "uncompressed size" in str(e).lower()

    # Verify HTTP endpoint returns 413 Payload Too Large
    resp = auth_client.post(
        "/api/analyze/file",
        files={"file": ("huge_uncompressed.zip", zip_bytes, "application/zip")}
    )
    assert resp.status_code == 413
    assert "uncompressed size" in resp.json()["detail"].lower()


def test_eml_plain_text():
    eml_content = (
        "From: Alice Morgan <alice@example.com>\n"
        "To: Bob Vance <bob@example.com>\n"
        "Cc: Charlie Green <charlie@example.com>\n"
        "Date: Fri, 24 May 2024 10:00:00 +0000\n"
        "Subject: Project Alpha Milestone Scope\n"
        "\n"
        "Hi Bob,\n"
        "\n"
        "We have confirmed the foundation inspection date for next Tuesday.\n"
        "Please bring the approved permits.\n"
        "\n"
        "Best,\n"
        "Alice\n"
    )
    res = extract_from_eml(eml_content.encode("utf-8"), "project_scope.eml")
    
    assert res.source_type == "Email Thread"
    assert "From: Alice Morgan" in res.full_text
    assert "Subject: Project Alpha Milestone Scope" in res.full_text
    assert "foundation inspection date" in res.full_text
    assert len(res.blocks) >= 2
    assert res.blocks[0].location == "Email Header"


def test_eml_html_only():
    msg = EmailMessage()
    msg["From"] = "david@example.com"
    msg["To"] = "team@example.com"
    msg["Subject"] = "HTML Update"
    msg["Date"] = "Fri, 24 May 2024 14:00:00 +0000"
    
    html_body = (
        "<html><head><script>alert('xss');</script><style>body{color:red;}</style></head>"
        "<body><h2>Project Milestone 2 Approved</h2>"
        "<p>The client approved the revised curtain wall drawings.</p>"
        "<p>Installation will proceed on June 1st.</p></body></html>"
    )
    msg.set_content(html_body, subtype="html")
    eml_bytes = msg.as_bytes()
    
    res = extract_from_eml(eml_bytes, "html_email.eml")
    assert res.source_type == "Email Thread"
    assert "alert(" not in res.full_text
    assert "Project Milestone 2 Approved" in res.full_text
    assert "Installation will proceed on June 1st" in res.full_text


def test_eml_multipart():
    msg = EmailMessage()
    msg["From"] = "elena@example.com"
    msg["To"] = "marcus@example.com"
    msg["Subject"] = "Multipart Coordination"
    msg.set_content("Plain text version: Ceiling framing scheduled for Friday.")
    msg.add_alternative("<p>HTML version: Ceiling framing scheduled for Friday.</p>", subtype="html")
    eml_bytes = msg.as_bytes()
    
    res = extract_from_eml(eml_bytes, "multipart.eml")
    assert "Ceiling framing scheduled for Friday" in res.full_text
    assert res.blocks[0].sender == "elena@example.com"


def test_eml_empty_body_rejected():
    eml_empty = "From: Alice <alice@example.com>\nTo: Bob <bob@example.com>\nSubject: Blank\n\n"
    try:
        extract_from_eml(eml_empty.encode("utf-8"), "blank.eml")
        assert False, "Should have raised EmptyFileError"
    except EmptyFileError:
        pass


def test_mbox_multi_message_archive():
    mbox_content = (
        "From alice@example.com Fri May 24 10:00:00 2024\n"
        "From: Alice <alice@example.com>\n"
        "To: Bob <bob@example.com>\n"
        "Date: Fri, 24 May 2024 10:00:00 +0000\n"
        "Subject: Thread 1\n"
        "\n"
        "Message 1: Initial project brief.\n"
        "\n"
        "From bob@example.com Fri May 24 11:00:00 2024\n"
        "From: Bob <bob@example.com>\n"
        "To: Alice <alice@example.com>\n"
        "Date: Fri, 24 May 2024 11:00:00 +0000\n"
        "Subject: Re: Thread 1\n"
        "\n"
        "Message 2: Budget approved for phase 1.\n"
    )
    res = extract_from_mbox(mbox_content.encode("utf-8"), "project_archive.mbox")
    assert res.source_type == "Email Thread"
    assert len(res.blocks) == 2
    assert "Initial project brief" in res.full_text
    assert "Budget approved for phase 1" in res.full_text


def test_guest_whatsapp_zip_extracted_text_oversized_rejected_413():
    long_chat = (
        "[24/05/2024, 10:00:00] Alice: " + "A" * 1600 + "\n"
    )
    zip_bytes = build_zip_archive({"_chat.txt": long_chat})
    
    response = guest_client.post(
        "/api/analyze/file",
        files={"file": ("whatsapp_oversized.zip", zip_bytes, "application/zip")}
    )
    assert response.status_code == 413
    data = response.json()
    assert "1,500" in data["detail"]
    assert "create a free account" in data["detail"].lower()


def test_authenticated_whatsapp_zip_oversized_succeeds():
    valid_long_chat = (
        "[24/05/2024, 10:00:00] Alice Morgan: Let us finalize all architectural milestones.\n"
        + ("[24/05/2024, 10:05:00] Bob Vance: Completed architectural review and approved structural schematics for phase 2.\n") * 32
    )
    zip_bytes = build_zip_archive({"_chat.txt": valid_long_chat})
    
    response = auth_client.post(
        "/api/analyze/file",
        files={"file": ("whatsapp_auth.zip", zip_bytes, "application/zip")}
    )
    assert response.status_code != 413
    if response.status_code == 200:
        data = response.json()
        assert len(data["keyPoints"]) >= 1


def test_guest_eml_oversized_rejected_413():
    long_eml = (
        "From: Alice <alice@example.com>\n"
        "To: Bob <bob@example.com>\n"
        "Subject: Oversized Email\n"
        "\n"
        + "This is a long email discussion sentence. " * 50
    )
    assert len(long_eml) > 1500
    
    response = guest_client.post(
        "/api/analyze/file",
        files={"file": ("oversized.eml", long_eml.encode("utf-8"), "message/rfc822")}
    )
    assert response.status_code == 413
    data = response.json()
    assert "1,500" in data["detail"]
    assert "create a free account" in data["detail"].lower()


def test_existing_inputs_regression():
    # TXT regression
    txt_res = process_uploaded_file(b"Line 1: Meeting\nLine 2: Action", "meeting.txt")
    assert txt_res.filename == "meeting.txt"
    assert len(txt_res.blocks) == 2
