from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone
from urllib.parse import urlencode
from datetime import date
from uuid import UUID
from v2.type_util.auth import AuthUser
from fastapi import Request
from v2.database_util import report as report_db

import os
import textwrap
import boto3
import structlog

logger = structlog.get_logger(__name__)

PDF_REPORT_BATCH_SIZE = 5000
PDF_REPORT_RETENTION_DAYS = 30
PDF_REPORT_S3_PART_SIZE = int(os.environ.get("FILE_REPORT_S3_PART_SIZE", str(16 * 1024 * 1024)))
PDF_REPORT_BUCKET = os.environ.get("FILE_REPORT_BUCKET", "cue-reports")
PDF_REPORT_PRESIGNED_URL_EXPIRATION = int(os.environ.get("FILE_REPORT_PRESIGNED_URL_EXPIRATION", "604800"))
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "cue-no-reply@nasa.gov")
VALID_FILE_STATUSES = {"unscanned", "clean", "infected", "scan_failed", "distributed"}

def _pdf_escape(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

class _S3MultipartWriter:
    """File-like writer that uploads buffered bytes to S3 multipart upload."""
    def __init__(self, s3_client, bucket: str, key: str, part_size: int = PDF_REPORT_S3_PART_SIZE):
        self.s3_client = s3_client
        self.bucket = bucket
        self.key = key
        self.part_size = max(part_size, 5 * 1024 * 1024)
        self.buffer = bytearray()
        self.parts: list[Dict[str, Any]] = []
        self.part_number = 1
        self.position = 0
        self.upload_id: Optional[str] = None

    def start(self, tagging: str, metadata: Dict[str, str]):
        response = self.s3_client.create_multipart_upload(
            Bucket=self.bucket,
            Key=self.key,
            ContentType="application/pdf",
            Tagging=tagging,
            Metadata=metadata,
        )
        self.upload_id = response["UploadId"]

    def write(self, data: bytes):
        if not data:
            return
        self.buffer.extend(data)
        self.position += len(data)
        while len(self.buffer) >= self.part_size:
            self._upload_part(bytes(self.buffer[:self.part_size]))
            del self.buffer[:self.part_size]

    def complete(self):
        if self.buffer:
            self._upload_part(bytes(self.buffer))
            self.buffer.clear()
        self.s3_client.complete_multipart_upload(
            Bucket=self.bucket,
            Key=self.key,
            UploadId=self.upload_id,
            MultipartUpload={"Parts": self.parts},
        )

    def abort(self):
        if self.upload_id:
            self.s3_client.abort_multipart_upload(Bucket=self.bucket, Key=self.key, UploadId=self.upload_id)

    def _upload_part(self, body: bytes):
        if self.part_number > 10000:
            raise ValueError("S3 multipart upload exceeded the 10,000 part limit. Increase FILE_REPORT_S3_PART_SIZE.")
        response = self.s3_client.upload_part(
            Bucket=self.bucket,
            Key=self.key,
            UploadId=self.upload_id,
            PartNumber=self.part_number,
            Body=body,
        )
        self.parts.append({"ETag": response["ETag"], "PartNumber": self.part_number})
        self.part_number += 1

class _StreamingPdfReport:
    """Streams a simple PDF document while keeping only PDF object offsets in memory."""
    def __init__(self, title: str, writer: _S3MultipartWriter):
        self.title = title
        self.writer = writer
        self.offsets: Dict[int, int] = {}
        self.page_object_ids: list[int] = []
        self.rows_per_page = 42
        self.current_lines: list[str] = []
        self.next_object_id = 3
        self.font_id = 1
        self.pages_id = 2

    def start(self):
        self._write(b"%PDF-1.4\n")
        self._write_object(self.font_id, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    def add_line(self, line: str):
        self.current_lines.append(line)
        if len(self.current_lines) >= self.rows_per_page:
            self._flush_page()

    def finish(self):
        self._flush_page()
        kids = " ".join(f"{page_id} 0 R" for page_id in self.page_object_ids)
        pages_object = f"<< /Type /Pages /Kids [{kids}] /Count {len(self.page_object_ids)} >>".encode("utf-8")
        self._write_object(self.pages_id, pages_object)
        catalog_id = self._allocate_object_id()
        self._write_object(catalog_id, f"<< /Type /Catalog /Pages {self.pages_id} 0 R >>".encode("utf-8"))
        self._write_xref(catalog_id)

    def _flush_page(self):
        if not self.current_lines and self.page_object_ids:
            return
        page_number = len(self.page_object_ids) + 1
        text_commands = ["BT", "/F1 10 Tf", "50 770 Td", f"({_pdf_escape(self.title)} - Page {page_number}) Tj"]
        text_commands.extend(["0 -18 Td", f"({_pdf_escape('-' * min(len(self.title), 80))}) Tj"])
        for line in self.current_lines:
            for wrapped_line in textwrap.wrap(line, width=110) or [""]:
                text_commands.extend(["0 -14 Td", f"({_pdf_escape(wrapped_line)}) Tj"])
        text_commands.append("ET")
        stream = "\n".join(text_commands).encode("utf-8")
        content_id = self._allocate_object_id()
        page_id = self._allocate_object_id()
        self._write_object(
            content_id,
            b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
        )
        self._write_object(
            page_id,
            f"<< /Type /Page /Parent {self.pages_id} 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {self.font_id} 0 R >> >> /Contents {content_id} 0 R >>"
            .encode("utf-8"),
        )
        self.page_object_ids.append(page_id)
        self.current_lines = []

    def _allocate_object_id(self) -> int:
        object_id = self.next_object_id
        self.next_object_id += 1
        return object_id

    def _write_object(self, object_id: int, content: bytes):
        self.offsets[object_id] = self.writer.position
        self._write(f"{object_id} 0 obj\n".encode("ascii"))
        self._write(content)
        self._write(b"\nendobj\n")

    def _write_xref(self, catalog_id: int):
        xref_offset = self.writer.position
        max_object_id = max(self.offsets)
        self._write(f"xref\n0 {max_object_id + 1}\n".encode("ascii"))
        self._write(b"0000000000 65535 f \n")
        for object_id in range(1, max_object_id + 1):
            self._write(f"{self.offsets[object_id]:010d} 00000 n \n".encode("ascii"))
        self._write(
            f"trailer\n<< /Size {max_object_id + 1} /Root {catalog_id} 0 R >>\nstartxref\n{xref_offset}\n%%EOF"
            .encode("ascii")
        )

    def _write(self, data: bytes):
        self.writer.write(data)

def _format_report_datetime(value: Any) -> str:
    if not value:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)

def _format_report_file_row(record: Dict[str, Any]) -> str:
    return (
        f"{record.get('name', '')} | "
        f"Collection: {record.get('collection_name') or record.get('collection_id', '')} | "
        f"Size: {record.get('size_bytes', '')} | "
        f"Uploaded: {_format_report_datetime(record.get('upload_time'))} | "
        f"Distributed: {_format_report_datetime(record.get('egress_start'))}"
    )

def _send_pdf_report_email(recipient: str, status: str, download_url: str, object_key: str):
    ses_client = boto3.client("ses", region_name=os.environ.get("SES_REGION", os.environ.get("AWS_REGION", "us-west-2")))
    subject = f"CUE {status} file report is ready"
    body_text = (
        f"Your CUE {status} file PDF report is ready.\n\n"
        f"Download link: {download_url}\n\n"
        f"The report object is tagged for deletion after {PDF_REPORT_RETENTION_DAYS} days.\n"
        f"S3 key: {object_key}"
    )
    body_html = (
        f"<p>Your CUE <strong>{status}</strong> file PDF report is ready.</p>"
        f"<p><a href=\"{download_url}\">Download the report</a></p>"
        f"<p>The report object is tagged for deletion after {PDF_REPORT_RETENTION_DAYS} days.</p>"
    )
    send_email_args = {
        "Source": SENDER_EMAIL,
        "Destination": {"ToAddresses": [recipient]},
        "Message": {
            "Subject": {"Data": subject},
            "Body": {
                "Text": {"Data": body_text},
                "Html": {"Data": body_html},
            },
        },
    }
    if os.environ.get("SES_SOURCE_ARN"):
        send_email_args["SourceArn"] = os.environ["SES_SOURCE_ARN"]
    if os.environ.get("SES_CONFIGURATION_SET_NAME"):
        send_email_args["ConfigurationSetName"] = os.environ["SES_CONFIGURATION_SET_NAME"]

    ses_client.send_email(**send_email_args)

async def generate_file_status_pdf_report(
    pool,
    requesting_user: Dict[str, Any],
    active_ngroup_id: Optional[UUID],
    status: str,
    recipient_email: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    """Background task that builds, uploads, and emails a file status PDF report."""
    report_id = UUID(requesting_user["id"]) if isinstance(requesting_user.get("id"), str) else requesting_user["id"]
    object_key = f"reports/file-status/{status}/{report_id}/{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.pdf"
    title = f"CUE {status} Files Report"
    header_lines = [
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Status: {status}",
        f"Start Date: {start_date or 'Any'}",
        f"End Date: {end_date or 'Any'}",
        "Total Rows: calculated when complete",
        "",
        "File Name | Collection | Size Bytes | Upload Time | Distributed Time",
    ]

    s3_client = boto3.client("s3", region_name=os.environ.get("AWS_REGION", "us-west-2"))
    multipart_writer = _S3MultipartWriter(s3_client, PDF_REPORT_BUCKET, object_key)
    multipart_writer.start(
        tagging=urlencode({
            "report_type": "file-status-pdf",
            "delete_after_days": str(PDF_REPORT_RETENTION_DAYS),
        }),
        metadata={
            "status": status,
            "generated_by": str(requesting_user.get("id")),
            "retention_days": str(PDF_REPORT_RETENTION_DAYS),
        },
    )
    pdf_report = _StreamingPdfReport(title, multipart_writer)

    offset = 0
    total_rows = 0
    try:
        pdf_report.start()
        for line in header_lines:
            pdf_report.add_line(line)

        while True:
            async with pool.acquire() as conn:
                batch = await report_db.list_files_for_status_pdf_report_batch(
                    conn,
                    requesting_user=requesting_user,
                    active_ngroup_id=active_ngroup_id,
                    status=status,
                    limit=PDF_REPORT_BATCH_SIZE,
                    offset=offset,
                    start_date=start_date,
                    end_date=end_date,
                )
            if not batch:
                break

            total_rows += len(batch)
            for record in batch:
                pdf_report.add_line(_format_report_file_row(dict(record)))
            offset += PDF_REPORT_BATCH_SIZE

        pdf_report.add_line("")
        pdf_report.add_line(f"Total Rows: {total_rows}")
        pdf_report.finish()
        multipart_writer.complete()
    except Exception:
        multipart_writer.abort()
        raise

    download_url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": PDF_REPORT_BUCKET, "Key": object_key},
        ExpiresIn=PDF_REPORT_PRESIGNED_URL_EXPIRATION,
    )
    _send_pdf_report_email(recipient_email, status, download_url, object_key)
    logger.info(
        "file.status_pdf_report.completed",
        status=status,
        recipient=recipient_email,
        rows=total_rows,
        s3_key=object_key,
    )

async def start_file_status_pdf_report(
    request: Request,
    user: AuthUser,
    active_ngroup_id: Optional[str],
    status: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> Dict[str, Optional[str]]:
    if not user.email:
        raise ValueError("User email is required to deliver the PDF report.")
    if status not in VALID_FILE_STATUSES:
        raise ValueError(f"Invalid status: {status}. Must be one of: {', '.join(sorted(VALID_FILE_STATUSES))}.")

    ngroup_id_to_filter = UUID(active_ngroup_id) if active_ngroup_id else None
    return {
        "message": "PDF report generation started. A download link will be emailed when the report is ready.",
        "status": status,
        "recipient_email": str(user.email),
        "active_ngroup_id": str(ngroup_id_to_filter) if ngroup_id_to_filter else None,
    }

