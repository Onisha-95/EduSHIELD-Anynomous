"""
Parsers package — dispatch based on file extension.
Supports: .pdf, .pptx, .docx, .txt
"""
import os

SUPPORTED = {".pdf", ".pptx", ".docx", ".txt"}


def parse_document(filepath: str) -> dict:
    """
    Parse any supported document and return a unified dict:
      {
        doc_id, source_file, format, title,
        sections: [{section_id, heading, content, location, bold_terms}],
        raw_text, all_bold_terms, parse_warnings, parse_success, parse_timestamp
      }
    """
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".pdf":
        from .pdf_parser import parse_pdf
        return parse_pdf(filepath)

    elif ext == ".pptx":
        from .pptx_parser import parse_pptx
        return parse_pptx(filepath)

    elif ext == ".docx":
        from .docx_parser import parse_docx
        return parse_docx(filepath)

    elif ext == ".txt":
        from .txt_parser import parse_txt
        return parse_txt(filepath)

    else:
        raise ValueError(
            f"Unsupported file type: {ext}. "
            f"Supported: {', '.join(sorted(SUPPORTED))}"
        )
