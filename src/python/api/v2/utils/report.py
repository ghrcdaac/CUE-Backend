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
import hmac
import hashlib
import time

logger = structlog.get_logger(__name__)

def generate_download_token(object_key: str, expires_at: int) -> str:
    """Generates a secure cryptographically-signed token for report download redirection."""
    secret = os.environ.get("PG_PASS", "default-cue-report-secret-key").encode("utf-8")
    msg = f"{object_key}:{expires_at}".encode("utf-8")
    signature = hmac.new(secret, msg, hashlib.sha256).hexdigest()
    return f"{expires_at}.{signature}"

def verify_download_token(object_key: str, token: str) -> bool:
    """Verifies the signature and expiration of a report download token."""
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return False
        expires_at_str, signature = parts
        expires_at = int(expires_at_str)
        if time.time() > expires_at:
            return False
        secret = os.environ.get("PG_PASS", "default-cue-report-secret-key").encode("utf-8")
        msg = f"{object_key}:{expires_at}".encode("utf-8")
        expected_signature = hmac.new(secret, msg, hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, expected_signature)
    except Exception:
        return False


PDF_REPORT_BATCH_SIZE = 5000
PDF_REPORT_RETENTION_DAYS = 30
PDF_REPORT_S3_PART_SIZE = int(str(16 * 1024 * 1024))
PDF_REPORT_BUCKET = os.environ.get("FILE_REPORT_BUCKET", "cue-reports")
PDF_REPORT_PRESIGNED_URL_EXPIRATION = int("604800")
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

def _truncate_text(value: Any, max_chars: int) -> str:
    text = "" if value is None else str(value)
    if len(text) > max_chars:
        return text[:max_chars - 3] + "..."
    return text

class _StreamingPdfReport:
    """Streams a simple PDF document while keeping only PDF object offsets in memory."""
    def __init__(self, title: str, writer: _S3MultipartWriter, metadata: List[str], table_headers: List[str]):
        self.title = title
        self.writer = writer
        self.metadata = metadata
        self.table_headers = table_headers
        self.offsets: Dict[int, int] = {}
        self.page_object_ids: list[int] = []
        self.current_rows: list[List[str]] = []
        self.next_object_id = 4  # Since font_id=1, pages_id=2, bold_font_id=3
        self.font_id = 1
        self.pages_id = 2
        self.bold_font_id = 3

    def start(self):
        self._write(b"%PDF-1.4\n")
        self._write_object(self.font_id, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        self._write_object(self.bold_font_id, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")

    def add_row(self, row: List[str]):
        self.current_rows.append(row)
        is_first_page = (len(self.page_object_ids) == 0)
        capacity = 47 if is_first_page else 54
        if len(self.current_rows) >= capacity:
            self._flush_page()

    def finish(self, total_rows: int):
        self._flush_page(total_rows=total_rows)
        kids = " ".join(f"{page_id} 0 R" for page_id in self.page_object_ids)
        pages_object = f"<< /Type /Pages /Kids [{kids}] /Count {len(self.page_object_ids)} >>".encode("utf-8")
        self._write_object(self.pages_id, pages_object)
        catalog_id = self._allocate_object_id()
        self._write_object(catalog_id, f"<< /Type /Catalog /Pages {self.pages_id} 0 R >>".encode("utf-8"))
        self._write_xref(catalog_id)

    def _flush_page(self, total_rows: Optional[int] = None):
        if not self.current_rows and self.page_object_ids and total_rows is None:
            return
        
        page_number = len(self.page_object_ids) + 1
        is_first_page = (page_number == 1)
        
        text_commands = []
        draw_commands = []
        
        # Title (Bold, 12pt)
        text_commands.extend([
            "BT",
            "/F2 12 Tf",
            "50 770 Td",
            f"({_pdf_escape(self.title)} - Page {page_number}) Tj"
        ])
        text_y = 770
        
        # Horizontal line below title
        draw_commands.extend([
            "1 w",
            "0.8 G",
            "50 758 m",
            "562 758 l",
            "S"
        ])
        
        if is_first_page:
            # Metadata block (Regular, 9pt, 13pt spacing)
            text_commands.extend([
                "/F1 9 Tf",
                "0 -18 Td"
            ])
            text_y -= 18
            for line in self.metadata:
                text_commands.extend([
                    f"({_pdf_escape(line)}) Tj",
                    "0 -13 Td"
                ])
                text_y -= 13
            text_commands.append("0 -5 Td")
            text_y -= 5
        else:
            text_commands.extend([
                "/F2 9 Tf",
                "0 -22 Td"
            ])
            text_y -= 22
            
        # Table Headers (Bold, 9pt)
        text_commands.append("/F2 9 Tf")
        col_offsets = [50, 210, 320, 382, 472]
        
        current_x = 50
        for i, header in enumerate(self.table_headers):
            if i > 0:
                dx = col_offsets[i] - col_offsets[i-1]
                text_commands.append(f"{dx} 0 Td")
                current_x = col_offsets[i]
            text_commands.append(f"({_pdf_escape(header)}) Tj")
            
        # Horizontal line below table headers
        draw_commands.extend([
            "0.5 w",
            "0.5 G",
            f"50 {text_y - 4} m",
            f"562 {text_y - 4} l",
            "S"
        ])
        
        # Data Rows (Regular, 8pt, 12pt spacing)
        dx = 50 - current_x
        text_commands.extend([
            "/F1 8 Tf",
            f"{dx} -14 Td"
        ])
        text_y -= 14
        current_x = 50
        
        for row in self.current_rows:
            col0 = _truncate_text(row[0] if len(row) > 0 else "", 36)
            col1 = _truncate_text(row[1] if len(row) > 1 else "", 24)
            col2 = _truncate_text(row[2] if len(row) > 2 else "", 14)
            col3 = _truncate_text(row[3] if len(row) > 3 else "", 20)
            col4 = _truncate_text(row[4] if len(row) > 4 else "", 20)
            
            row_cols = [col0, col1, col2, col3, col4]
            for i, val in enumerate(row_cols):
                if i > 0:
                    dx_col = col_offsets[i] - col_offsets[i-1]
                    text_commands.append(f"{dx_col} 0 Td")
                    current_x = col_offsets[i]
                text_commands.append(f"({_pdf_escape(val)}) Tj")
                
            dx = 50 - current_x
            text_commands.append(f"{dx} -12 Td")
            text_y -= 12
            current_x = 50
            
        if total_rows is not None:
            # Draw line under last row
            draw_commands.extend([
                "0.5 w",
                "0.5 G",
                f"50 {text_y + 8} m",
                f"562 {text_y + 8} l",
                "S"
            ])
            text_commands.extend([
                "/F2 9 Tf",
                "0 -16 Td",
                f"(Total Rows: {total_rows}) Tj"
            ])
            
        text_commands.append("ET")
        
        page_stream = "\n".join(draw_commands + text_commands).encode("utf-8")
        
        content_id = self._allocate_object_id()
        page_id = self._allocate_object_id()
        self._write_object(
            content_id,
            b"<< /Length " + str(len(page_stream)).encode("ascii") + b" >>\nstream\n" + page_stream + b"\nendstream",
        )
        self._write_object(
            page_id,
            f"<< /Type /Page /Parent {self.pages_id} 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {self.font_id} 0 R /F2 {self.bold_font_id} 0 R >> >> /Contents {content_id} 0 R >>"
            .encode("utf-8"),
        )
        self.page_object_ids.append(page_id)
        self.current_rows = []

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
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)

def _format_report_file_row_cols(record: Dict[str, Any]) -> List[str]:
    return [
        record.get("name") or "",
        record.get("collection_name") or record.get("collection_id") or "",
        str(record.get("size_bytes") if record.get("size_bytes") is not None else ""),
        _format_report_datetime(record.get("upload_time")),
        _format_report_datetime(record.get("egress_start")),
    ]

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
    end_date: Optional[date] = None,
    base_url: str = "http://localhost:8000/",
    root_path: str = ""
):
    """Triggers the AWS Glue Job to build and email the file status PDF report."""
    logger.info(
        "file.status_pdf_report.triggering_glue",
        status=status,
        recipient=recipient_email,
        requesting_user_id=str(requesting_user.get("id")),
    )

    glue_client = boto3.client("glue", region_name=os.environ.get("AWS_REGION", "us-west-2"))
    
    username = requesting_user.get("cueusername") or requesting_user.get("preferred_username") or requesting_user.get("name") or "Unknown"
    user_roles = requesting_user.get("roles", [])
    roles_str = ",".join(user_roles) if isinstance(user_roles, list) else ""

    try:
        response = glue_client.start_job_run(
            JobName="file_status_report_generator",
            Arguments={
                "--RECIPIENT_EMAIL": recipient_email,
                "--STATUS": status,
                "--START_DATE": start_date.isoformat() if start_date else "",
                "--END_DATE": end_date.isoformat() if end_date else "",
                "--ACTIVE_NGROUP_ID": str(active_ngroup_id) if active_ngroup_id else "",
                "--REQUESTING_USER_ID": str(requesting_user.get("id", "")),
                "--REQUESTING_USER_NAME": username,
                "--REQUESTING_USER_ROLES": roles_str,
                "--BASE_URL": base_url,
                "--ROOT_PATH": root_path,
            }
        )
        logger.info(
            "file.status_pdf_report.glue_triggered",
            status=status,
            recipient=recipient_email,
            job_run_id=response.get("JobRunId"),
        )
    except Exception as e:
        logger.error(
            "file.status_pdf_report.glue_trigger_failed",
            status=status,
            recipient=recipient_email,
            error=str(e),
            exc_info=True
        )
        raise


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

