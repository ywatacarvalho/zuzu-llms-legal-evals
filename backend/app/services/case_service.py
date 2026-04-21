import io

import pdfplumber
from fastapi import UploadFile


async def extract_text_from_pdf(file: UploadFile) -> str:
    content = await file.read()
    pages: list[str] = []

    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text and text.strip():
                pages.append(text.strip())

    return "\n\n".join(pages)


def derive_title(filename: str) -> str:
    """Strip extension and humanise the filename as a case title."""
    stem = filename.rsplit(".", 1)[0]
    return stem.replace("_", " ").replace("-", " ").title()
