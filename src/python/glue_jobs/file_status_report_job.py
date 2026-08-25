import sys
import os
import boto3
import asyncio
import asyncpg
import structlog
import logging
import hmac
import hashlib
import time
from datetime import datetime, timezone, date
from uuid import UUID
from typing import List, Dict, Any, Tuple, Optional
from urllib.parse import urlencode
try:
    from awsglue.utils import getResolvedOptions
except ImportError:
    def getResolvedOptions(args, options):
        resolved = {}
        for opt in options:
            val = os.environ.get(opt)
            if not val:
                for i, arg in enumerate(sys.argv):
                    if arg == f"--{opt}" and i + 1 < len(sys.argv):
                        val = sys.argv[i + 1]
                        break
            resolved[opt] = val or ""
        return resolved


# --- Setup Logging ---
shared_processors = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_logger_name,
    structlog.stdlib.add_log_level,
    structlog.processors.TimeStamper(fmt="iso"),
]
processors = shared_processors + [
    structlog.stdlib.PositionalArgumentsFormatter(),
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
    structlog.processors.JSONRenderer(),
]
log_level = logging.INFO

logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=log_level,
    force=True
)

structlog.configure(
    processors=processors,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# --- PDF Generation Constants ---
PDF_REPORT_BATCH_SIZE = 5000
PDF_REPORT_RETENTION_DAYS = 30
PDF_REPORT_S3_PART_SIZE = 16 * 1024 * 1024

def _pdf_escape(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

def _truncate_text(value: Any, max_chars: int) -> str:
    text = "" if value is None else str(value)
    if len(text) > max_chars:
        return text[:max_chars - 3] + "..."
    return text

class _S3MultipartWriter:
    def __init__(self, s3_client, bucket: str, key: str, part_size: int = PDF_REPORT_S3_PART_SIZE):
        self.s3_client = s3_client
        self.bucket = bucket
        self.key = key
        self.part_size = max(part_size, 5 * 1024 * 1024)
        self.buffer = bytearray()
        self.parts = []
        self.part_number = 1
        self.position = 0
        self.upload_id = None

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
            try:
                self.s3_client.abort_multipart_upload(Bucket=self.bucket, Key=self.key, UploadId=self.upload_id)
            except Exception as e:
                logger.error("s3.abort_multipart_upload.failed", error=str(e))

    def _upload_part(self, body: bytes):
        if self.part_number > 10000:
            raise ValueError("S3 multipart upload exceeded 10,000 part limit.")
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
    def __init__(self, title: str, writer: _S3MultipartWriter, metadata: List[str], table_headers: List[str]):
        self.title = title
        self.writer = writer
        self.metadata = metadata
        self.table_headers = table_headers
        self.offsets = {}
        self.page_object_ids = []
        self.current_rows = []
        self.next_object_id = 4
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
        text_commands.extend([
            "BT",
            "/F2 12 Tf",
            "50 770 Td",
            f"({_pdf_escape(self.title)} - Page {page_number}) Tj"
        ])
        text_y = 770
        draw_commands.extend([
            "1 w",
            "0.8 G",
            "50 758 m",
            "562 758 l",
            "S"
        ])
        if is_first_page:
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
        text_commands.append("/F2 9 Tf")
        col_offsets = [50, 210, 320, 382, 472]
        current_x = 50
        for i, header in enumerate(self.table_headers):
            if i > 0:
                dx = col_offsets[i] - col_offsets[i-1]
                text_commands.append(f"{dx} 0 Td")
                current_x = col_offsets[i]
            text_commands.append(f"({_pdf_escape(header)}) Tj")
        draw_commands.extend([
            "0.5 w",
            "0.5 G",
            f"50 {text_y - 4} m",
            f"562 {text_y - 4} l",
            "S"
        ])
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

# --- Date Formatting Helpers ---
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

# --- Database Query ---
async def list_files_for_status_pdf_report_batch(
    conn: asyncpg.Connection,
    requesting_user: Dict[str, Any],
    active_ngroup_id: Optional[UUID],
    status: str,
    limit: int,
    offset: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> List[asyncpg.Record]:
    user_roles = set(requesting_user.get('roles', []))
    params = [status]
    base_query = """
        SELECT
            f.id, f.name, f.type, f.size_bytes, f.collection_id, c.short_name AS collection_name,
            fs.status, fs.upload_time, fs.egress_start
        FROM file f
        JOIN collection c ON f.collection_id = c.id
        LEFT JOIN file_status fs ON f.id = fs.id
    """
    where_conditions = ["f.name != 'pending_upload'", "fs.status = $1"]
    if active_ngroup_id:
        params.append(active_ngroup_id)
        where_conditions.append(f"c.ngroup_id = ${len(params)}")
    else:
        if 'admin' not in user_roles and 'security' not in user_roles:
            where_conditions.append("FALSE")
    if start_date:
        params.append(start_date)
        where_conditions.append(f"fs.upload_time >= ${len(params)}")
    if end_date:
        params.append(end_date)
        where_conditions.append(f"fs.upload_time < (${len(params)}::date + 1)")
    query = f"""
        {base_query}
        WHERE {' AND '.join(where_conditions)}
        ORDER BY fs.upload_time DESC, f.id
        LIMIT ${len(params) + 1} OFFSET ${len(params) + 2};
    """
    params.extend([limit, offset])
    return await conn.fetch(query, *params)

# --- Signed Redirect Link Generation ---
def generate_download_token(object_key: str, expires_at: int, db_pass: str) -> str:
    secret = db_pass.encode("utf-8")
    msg = f"{object_key}:{expires_at}".encode("utf-8")
    signature = hmac.new(secret, msg, hashlib.sha256).hexdigest()
    return f"{expires_at}.{signature}"

# --- SES Email Sender ---
def send_pdf_report_email(args: Dict[str, Any], recipient: str, status: str, download_url: str, object_key: str):
    ses_client = boto3.client("ses", region_name=args.get("SES_REGION", os.environ.get("AWS_REGION", "us-west-2")))
    sender = args["SENDER_EMAIL"]
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
        "Source": sender,
        "Destination": {"ToAddresses": [recipient]},
        "Message": {
            "Subject": {"Data": subject},
            "Body": {
                "Text": {"Data": body_text},
                "Html": {"Data": body_html},
            },
        },
    }
    if args.get("SES_SOURCE_ARN"):
        send_email_args["SourceArn"] = args["SES_SOURCE_ARN"]
    if args.get("SES_CONFIGURATION_SET_NAME"):
        send_email_args["ConfigurationSetName"] = args["SES_CONFIGURATION_SET_NAME"]

    ses_client.send_email(**send_email_args)

# --- Main Entrypoint ---
async def run_report_generation(args: Dict[str, Any]):
    db_host = args["PG_HOST"]
    db_port = int(args["PG_PORT"])
    db_name = args["PG_DB"]
    db_user = args["PG_USER"]
    db_pass = args["PG_PASS"]
    status = args["STATUS"]
    recipient_email = args["RECIPIENT_EMAIL"]
    requesting_user_id = args["REQUESTING_USER_ID"]
    username = args["REQUESTING_USER_NAME"]
    
    # Parse dates
    start_date = None
    if args.get("START_DATE"):
        start_date = date.fromisoformat(args["START_DATE"])
    end_date = None
    if args.get("END_DATE"):
        end_date = date.fromisoformat(args["END_DATE"])
        
    active_ngroup_id = None
    if args.get("ACTIVE_NGROUP_ID"):
        active_ngroup_id = UUID(args["ACTIVE_NGROUP_ID"])

    requesting_user = {
        "id": requesting_user_id,
        "roles": [r for r in args.get("REQUESTING_USER_ROLES", "").split(",") if r]
    }

    object_key = f"reports/file-status/{status}/{requesting_user_id}/{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.pdf"
    title = f"CUE {status} Files Report"
    metadata_lines = [
        f"Username: {username}",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Status: {status}",
        f"Start Date: {start_date or 'Any'}",
        f"End Date: {end_date or 'Any'}",
    ]
    table_headers = ["File Name", "Collection", "Size (Bytes)", "Uploaded", "Distributed"]

    # Connect to S3 and start Multipart Upload
    s3_client = boto3.client("s3", region_name=os.environ.get("AWS_REGION", "us-west-2"))
    bucket = args["FILE_REPORT_BUCKET"]
    multipart_writer = _S3MultipartWriter(s3_client, bucket, object_key)
    multipart_writer.start(
        tagging=urlencode({
            "report_type": "file-status-pdf",
            "delete_after_days": str(PDF_REPORT_RETENTION_DAYS),
        }),
        metadata={
            "status": status,
            "generated_by": requesting_user_id,
            "retention_days": str(PDF_REPORT_RETENTION_DAYS),
        },
    )

    pdf_report = _StreamingPdfReport(title, multipart_writer, metadata_lines, table_headers)
    offset = 0
    total_rows = 0

    try:
        pdf_report.start()
        # Connect to Database
        conn = await asyncpg.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_pass,
            ssl="require"
        )
        try:
            while True:
                batch = await list_files_for_status_pdf_report_batch(
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
                    pdf_report.add_row(_format_report_file_row_cols(dict(record)))
                offset += PDF_REPORT_BATCH_SIZE
        finally:
            await conn.close()

        pdf_report.finish(total_rows)
        multipart_writer.complete()
    except Exception as e:
        multipart_writer.abort()
        logger.error("glue_job.report_generation.failed", error=str(e), exc_info=True)
        raise e

    # Generate redirect URL using signed download token
    base_url = args["BASE_URL"]
    root_path = args["ROOT_PATH"]
    expires_at = int(time.time()) + (PDF_REPORT_RETENTION_DAYS * 24 * 3600)
    token = generate_download_token(object_key, expires_at, db_pass)
    download_url = f"{base_url.rstrip('/')}{root_path}/v2/reports/download?key={object_key}&token={token}"

    # Send Email
    send_pdf_report_email(args, recipient_email, status, download_url, object_key)
    logger.info("glue_job.report_generation.completed", status=status, recipient=recipient_email, rows=total_rows, key=object_key)

if __name__ == "__main__":
    resolved_args = getResolvedOptions(
        sys.argv,
        [
            "PG_HOST",
            "PG_PORT",
            "PG_DB",
            "PG_USER",
            "PG_PASS",
            "FILE_REPORT_BUCKET",
            "SENDER_EMAIL",
            "SES_REGION",
            "SES_SOURCE_ARN",
            "SES_CONFIGURATION_SET_NAME",
            "RECIPIENT_EMAIL",
            "STATUS",
            "START_DATE",
            "END_DATE",
            "ACTIVE_NGROUP_ID",
            "REQUESTING_USER_ID",
            "REQUESTING_USER_NAME",
            "REQUESTING_USER_ROLES",
            "BASE_URL",
            "ROOT_PATH",
        ]
    )
    asyncio.run(run_report_generation(resolved_args))
