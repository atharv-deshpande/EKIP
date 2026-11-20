
from io import BytesIO

from fastapi.testclient import TestClient
from docx import Document
from pypdf import PdfWriter

from app.main import app


client = TestClient(app)


def create_docx() -> bytes:
    document = Document()
    document.add_heading("Payments", level=1)
    document.add_paragraph(
        "Payment processing must follow approved bank policies."
    )

    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def create_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)

    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["message"] == "Welcome to EKIP"


def test_upload_html_success():
    content = b"""
    <!DOCTYPE html>
    <html>
      <head><title>Payments Policy</title></head>
      <body>
        <h1>Payments</h1>
        <p>Payment processing must follow approved policies.</p>
      </body>
    </html>
    """

    response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "payments.html",
                content,
                "text/html",
            )
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["document_name"] == "payments.html"
    assert data["file_type"] == "html"
    assert data["status"] == "processed"
    assert data["total_chunks"] >= 1
    assert data["metadata"]["title"] == "Payments Policy"


def test_upload_docx_success():
    response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "payments.docx",
                create_docx(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["file_type"] == "docx"
    assert data["status"] == "processed"
    assert data["total_chunks"] >= 1


def test_upload_pdf_success():
    response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "blank.pdf",
                create_pdf(),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["file_type"] == "pdf"
    assert data["status"] == "processed"
    assert data["total_chunks"] == 0


def test_reject_unsupported_file():
    response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "notes.txt",
                b"Some plain text",
                "text/plain",
            )
        },
    )

    assert response.status_code == 415


def test_reject_invalid_html():
    response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "invalid.html",
                b"This is not HTML",
                "text/html",
            )
        },
    )

    assert response.status_code == 415
