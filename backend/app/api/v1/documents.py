
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.modules.ingestion.validators import validate_upload

from app.modules.ingestion.parsers.pdf_parser import (
    parse_pdf,
    PDFParserError,
)
from app.modules.ingestion.parsers.docx_parser import (
    parse_docx,
    DOCXParserError,
)
from app.modules.ingestion.parsers.html_parser import (
    parse_html,
    HTMLParserError,
)

from app.modules.ingestion.processing.ingestion_service import (
    process_parsed_document,
)


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


class ChunkResponse(BaseModel):
    chunk_index: int
    content: str
    token_count: int
    page_number: int | None
    section_title: str | None
    source_block_start: int
    source_block_end: int


class DocumentUploadResponse(BaseModel):
    document_name: str
    file_type: str
    status: str
    file_size: int
    total_chunks: int
    total_tokens: int
    metadata: dict
    chunks: list[ChunkResponse]


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=200,
)
async def upload_document(
    file: UploadFile = File(...),
):
    # Step 1: Validate uploaded file.
    validated = await validate_upload(file)

    # Step 2: Select parser.
    try:
        if validated.extension == ".pdf":
            parsed_document = parse_pdf(
                validated.content,
                validated.filename,
            )

        elif validated.extension == ".docx":
            parsed_document = parse_docx(
                validated.content,
                validated.filename,
            )

        elif validated.extension in {".html", ".htm"}:
            parsed_document = parse_html(
                validated.content,
                validated.filename,
            )

        else:
            raise HTTPException(
                status_code=415,
                detail="Unsupported document format.",
            )

        # Step 3: Normalize and generate chunks.
        result = process_parsed_document(parsed_document)

    except (PDFParserError, DOCXParserError, HTMLParserError) as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Document parsing failed: {exc}",
        ) from exc

    except TypeError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Document processing failed: {exc}",
        ) from exc

    # Step 4: Prepare response.
    return DocumentUploadResponse(
        document_name=result.document_name,
        file_type=result.file_type,
        status="processed",
        file_size=validated.size,
        total_chunks=result.total_chunks,
        total_tokens=result.total_tokens,
        metadata=result.metadata,
        chunks=[
            ChunkResponse(
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                token_count=chunk.token_count,
                page_number=chunk.page_number,
                section_title=chunk.section_title,
                source_block_start=chunk.source_block_start,
                source_block_end=chunk.source_block_end,
            )
            for chunk in result.chunks
        ],
    )
