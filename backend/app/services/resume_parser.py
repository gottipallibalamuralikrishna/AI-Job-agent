
from pathlib import Path

import fitz
from docx import Document
from fastapi import HTTPException


MAX_EXTRACTED_CHARACTERS = 200_000


class ResumeParser:

    @staticmethod
    def extract_pdf(file_path: Path) -> str:
        try:
            with fitz.open(file_path) as document:

                if document.needs_pass:
                    raise HTTPException(
                        status_code=400,
                        detail="Password-protected PDFs are not supported",
                    )

                if document.page_count == 0:
                    raise HTTPException(
                        status_code=400,
                        detail="PDF contains no pages",
                    )

                text_parts = []

                for page in document:
                    text_parts.append(page.get_text("text"))

                extracted_text = "\n".join(text_parts).strip()

                return extracted_text

        except HTTPException:
            raise

        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail="Unable to read the PDF document",
            ) from exc

    @staticmethod
    def extract_docx(file_path: Path) -> str:
        try:
            document = Document(file_path)

            text_parts = []

            # Extract paragraphs
            for paragraph in document.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text)

            # Extract tables
            for table in document.tables:
                for row in table.rows:
                    row_text = [
                        cell.text.strip()
                        for cell in row.cells
                        if cell.text.strip()
                    ]

                    if row_text:
                        text_parts.append(" | ".join(row_text))

            return "\n".join(text_parts).strip()

        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail="Unable to read the DOCX document",
            ) from exc

    @classmethod
    def extract_text(
        cls,
        file_path: Path,
        content_type: str,
    ) -> str:

        if content_type == "application/pdf":
            extracted_text = cls.extract_pdf(file_path)

        elif content_type == (
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ):
            extracted_text = cls.extract_docx(file_path)

        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported document format",
            )

        if not extracted_text:
            raise HTTPException(
                status_code=422,
                detail=(
                    "No readable text found. "
                    "The document may be scanned or image-based."
                ),
            )

        if len(extracted_text) > MAX_EXTRACTED_CHARACTERS:
            raise HTTPException(
                status_code=413,
                detail="Extracted document text exceeds the allowed limit",
            )

        return extracted_text
