import io
import os
import re
from dataclasses import dataclass, field
from typing import List, Optional, Literal
import pymupdf as fitz
import docx

MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB safety limit
SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx", ".chat", ".log", ".csv"}


class FileProcessingError(Exception):
    """Base exception for file processing."""
    pass


class UnsupportedFileTypeError(FileProcessingError):
    """Raised when an uploaded file extension or content is unsupported."""
    pass


class FileOversizedError(FileProcessingError):
    """Raised when an uploaded file exceeds the configured size limit."""
    pass


class EmptyFileError(FileProcessingError):
    """Raised when an uploaded file is empty or contains no extractable text."""
    pass


class NoSelectableTextPDFError(FileProcessingError):
    """Raised when a PDF contains no selectable text (e.g., scanned/image-only)."""
    pass


@dataclass
class ContentBlock:
    text: str
    source_name: str
    source_type: Literal["Chat Export", "Email Thread", "Meeting Transcript", "Document"]
    location: str
    sender: Optional[str] = None


@dataclass
class ExtractedFileContent:
    filename: str
    source_type: Literal["Chat Export", "Email Thread", "Meeting Transcript", "Document"]
    full_text: str
    blocks: List[ContentBlock] = field(default_factory=list)


def parse_sender_from_line(line: str) -> Optional[str]:
    """Extracts speaker/sender name if matching common chat/transcript patterns."""
    # Pattern: [timestamp] Speaker: message OR Speaker: message OR timestamp - Speaker: message
    patterns = [
        r"^\[.*?\]\s*([^:]+?)\s*:",                 # [10/12/2024, 08:34] David Miller: ...
        r"^\d{1,2}:\d{2}(?::\d{2})?\s*-\s*([^:]+?)\s*:", # 08:34 - David Miller: ...
        r"^([A-Z][A-Za-z0-9\s.()-]{1,35})\s*:",     # David Miller (Client): ...
    ]
    for pat in patterns:
        m = re.match(pat, line.strip())
        if m:
            candidate = m.group(1).strip()
            # Ignore common false positives like "Note:", "Date:", "Time:"
            if candidate.lower() not in {"note", "date", "time", "http", "https", "subject"}:
                return candidate
    return None


def decode_text_file_bytes(file_bytes: bytes, filename: str) -> str:
    """
    Decodes text file bytes using BOM detection, Windows Notepad encodings,
    and safe fallbacks (UTF-8, UTF-8 with BOM, UTF-16 LE, UTF-16 BE, CP1252).
    Prevents corrupt latin-1 decoding of UTF-16 files.
    """
    if not file_bytes or not file_bytes.strip():
        raise EmptyFileError(f"The file '{filename}' is empty or contains no text.")

    # 1. Explicit BOM detection
    if file_bytes.startswith(b"\xef\xbb\xbf"):
        return file_bytes[3:].decode("utf-8", errors="replace")
    elif file_bytes.startswith(b"\xff\xfe\x00\x00"):
        return file_bytes[4:].decode("utf-32-le", errors="replace")
    elif file_bytes.startswith(b"\x00\x00\xfe\xff"):
        return file_bytes[4:].decode("utf-32-be", errors="replace")
    elif file_bytes.startswith(b"\xff\xfe"):
        return file_bytes[2:].decode("utf-16-le", errors="replace")
    elif file_bytes.startswith(b"\xfe\xff"):
        return file_bytes[2:].decode("utf-16-be", errors="replace")

    # 2. Heuristic for UTF-16 without BOM (common in Windows Notepad / PowerShell exports)
    # Detect high frequency of alternating null bytes
    if len(file_bytes) >= 2 and (file_bytes[1::2].count(b"\x00") > len(file_bytes) // 4):
        try:
            decoded = file_bytes.decode("utf-16-le")
            if "\x00" not in decoded:
                return decoded
        except UnicodeDecodeError:
            pass
    elif len(file_bytes) >= 2 and (file_bytes[0::2].count(b"\x00") > len(file_bytes) // 4):
        try:
            decoded = file_bytes.decode("utf-16-be")
            if "\x00" not in decoded:
                return decoded
        except UnicodeDecodeError:
            pass

    # 3. Standard UTF-8 without BOM (must not contain null bytes)
    try:
        decoded = file_bytes.decode("utf-8")
        if "\x00" not in decoded:
            return decoded
    except UnicodeDecodeError:
        pass

    # 4. Standard Windows-1252 (ANSI Windows default)
    try:
        decoded = file_bytes.decode("cp1252")
        if "\x00" not in decoded:
            return decoded
    except UnicodeDecodeError:
        pass

    # 5. Latin-1 fallback with null-byte sanitization
    try:
        decoded = file_bytes.decode("latin-1", errors="replace")
        cleaned = decoded.replace("\x00", "")
        if cleaned.strip():
            return cleaned
    except Exception:
        pass

    raise FileProcessingError(f"Could not decode text file '{filename}'. Please ensure it is saved in a supported text encoding (UTF-8, UTF-16, or ANSI).")


def extract_from_txt(file_bytes: bytes, filename: str) -> ExtractedFileContent:
    """Extracts text from TXT or chat export files, supporting multiple encodings."""
    text = decode_text_file_bytes(file_bytes, filename)
    if not text or not text.strip():
        raise EmptyFileError(f"The file '{filename}' is empty or contains no text.")

    # Determine if chat export or general document
    is_chat = any(parse_sender_from_line(line) for line in text.splitlines()[:20])
    source_type: Literal["Chat Export", "Document"] = "Chat Export" if is_chat else "Document"

    lines = [l for l in text.splitlines()]
    blocks: List[ContentBlock] = []
    full_text_lines: List[str] = []

    message_idx = 1
    for line_idx, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue

        sender = parse_sender_from_line(line)
        location = f"Message #{message_idx}" if (is_chat and sender) else f"Line {line_idx}"
        if sender and is_chat:
            message_idx += 1

        blocks.append(
            ContentBlock(
                text=line,
                source_name=filename,
                source_type=source_type,
                location=location,
                sender=sender,
            )
        )
        full_text_lines.append(line)

    full_text = "\n".join(full_text_lines).strip()
    if not full_text:
        raise EmptyFileError(f"The file '{filename}' contains only whitespace or blank lines.")

    return ExtractedFileContent(
        filename=filename,
        source_type=source_type,
        full_text=full_text,
        blocks=blocks,
    )


def extract_from_pdf(file_bytes: bytes, filename: str) -> ExtractedFileContent:
    """Extracts text page-by-page from PDF using PyMuPDF."""
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        raise FileProcessingError(f"Failed to open PDF '{filename}': {str(e)}") from e

    try:
        if len(doc) == 0:
            raise EmptyFileError(f"The PDF '{filename}' contains 0 pages.")

        blocks: List[ContentBlock] = []
        full_text_parts: List[str] = []
        total_extracted_chars = 0

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            page_text = page.get_text("text").strip()
            page_num = page_idx + 1

            if page_text:
                total_extracted_chars += len(page_text)
                for line in page_text.splitlines():
                    clean_line = line.strip()
                    if clean_line:
                        sender = parse_sender_from_line(clean_line)
                        blocks.append(
                            ContentBlock(
                                text=clean_line,
                                source_name=filename,
                                source_type="Document",
                                location=f"Page {page_num}",
                                sender=sender,
                            )
                        )
                full_text_parts.append(f"[Page {page_num}]\n{page_text}")

        if total_extracted_chars == 0:
            raise NoSelectableTextPDFError(
                "This PDF does not contain selectable text. Scanned PDF/OCR support is not available yet."
            )

        full_text = "\n\n".join(full_text_parts).strip()
        return ExtractedFileContent(
            filename=filename,
            source_type="Document",
            full_text=full_text,
            blocks=blocks,
        )
    finally:
        doc.close()


def extract_from_docx(file_bytes: bytes, filename: str) -> ExtractedFileContent:
    """Extracts text paragraph-by-paragraph from DOCX using python-docx."""
    try:
        doc = docx.Document(io.BytesIO(file_bytes))
    except Exception as e:
        raise FileProcessingError(f"Failed to read Word document '{filename}': {str(e)}") from e

    blocks: List[ContentBlock] = []
    full_text_parts: List[str] = []
    current_section: Optional[str] = None
    para_count = 0

    for p in doc.paragraphs:
        p_text = p.text.strip()
        if not p_text:
            continue

        para_count += 1
        # Check if heading
        if p.style and p.style.name and p.style.name.startswith("Heading"):
            current_section = p_text

        location = f"Section '{current_section}' (Para {para_count})" if current_section else f"Paragraph {para_count}"
        sender = parse_sender_from_line(p_text)

        blocks.append(
            ContentBlock(
                text=p_text,
                source_name=filename,
                source_type="Document",
                location=location,
                sender=sender,
            )
        )
        full_text_parts.append(p_text)

    # Also extract tables if present
    for table_idx, table in enumerate(doc.tables, start=1):
        for row_idx, row in enumerate(table.rows, start=1):
            row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
            if row_text:
                blocks.append(
                    ContentBlock(
                        text=row_text,
                        source_name=filename,
                        source_type="Document",
                        location=f"Table {table_idx}, Row {row_idx}",
                    )
                )
                full_text_parts.append(row_text)

    if not full_text_parts:
        raise EmptyFileError(f"The document '{filename}' contains no readable text.")

    full_text = "\n\n".join(full_text_parts).strip()
    return ExtractedFileContent(
        filename=filename,
        source_type="Document",
        full_text=full_text,
        blocks=blocks,
    )


def process_uploaded_file(file_bytes: bytes, filename: str) -> ExtractedFileContent:
    """
    Validates file size and extension, then routes to the appropriate parser.
    Returns normalized text and granular location ContentBlocks.
    """
    if not filename:
        raise UnsupportedFileTypeError("Missing filename in uploaded file.")

    if len(file_bytes) == 0:
        raise EmptyFileError(f"Uploaded file '{filename}' is empty (0 bytes).")

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        max_mb = MAX_FILE_SIZE_BYTES // (1024 * 1024)
        raise FileOversizedError(f"File '{filename}' exceeds maximum allowed size of {max_mb} MB.")

    _, ext = os.path.splitext(filename.lower())
    if ext not in SUPPORTED_EXTENSIONS:
        supported_str = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise UnsupportedFileTypeError(
            f"Unsupported file format '{ext}'. Supported formats: {supported_str}"
        )

    if ext in {".txt", ".chat", ".log", ".csv"}:
        return extract_from_txt(file_bytes, filename)
    elif ext == ".pdf":
        return extract_from_pdf(file_bytes, filename)
    elif ext == ".docx":
        return extract_from_docx(file_bytes, filename)
    else:
        raise UnsupportedFileTypeError(f"Unsupported file format '{ext}'")
