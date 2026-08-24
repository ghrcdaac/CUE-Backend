from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, Request, Header
from fastapi.responses import RedirectResponse
from uuid import UUID
from typing import Optional
import os
import boto3

from core.security import get_current_user, require_privilege
from v2.type_util.auth import AuthUser
from v2.utils import report as report_utils
from v2.type_util.report import (
    FileStatusPdfReportRequest,
    FileStatusPdfReportResponse,
)

router = APIRouter(prefix="/reports", tags=["V2 - Reports"])

@router.get("/download")
async def download_report_endpoint(
    key: str,
    token: str,
):
    """Generates a fresh presigned S3 URL and redirects the user to download the report."""
    if not key.startswith("reports/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid report key."
        )

    if not report_utils.verify_download_token(key, token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Link is invalid or has expired."
        )

    try:
        s3_client = boto3.client("s3", region_name=os.environ.get("AWS_REGION", "us-west-2"))
        download_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": report_utils.PDF_REPORT_BUCKET, "Key": key},
            ExpiresIn=900,  # Valid for 15 minutes
        )
        return RedirectResponse(url=download_url)
    except Exception as e:
        report_utils.logger.error("report.download_redirect.failed", key=key, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate download URL."
        )

@router.post("/status-pdf", response_model=FileStatusPdfReportResponse, dependencies=[Depends(require_privilege("file:read"))])
async def request_file_status_pdf_report_endpoint(
    request: Request,
    background_tasks: BackgroundTasks,
    body: FileStatusPdfReportRequest,
    user: AuthUser = Depends(get_current_user),
    active_ngroup_id: Optional[str] = Header(None, alias="x-active-ngroup-id")
):
    """Starts background PDF report generation for files matching a status."""
    try:
        report_request = await report_utils.start_file_status_pdf_report(
            request,
            user,
            active_ngroup_id,
            body.status,
            body.start_date,
            body.end_date,
        )
        background_tasks.add_task(
            report_utils.generate_file_status_pdf_report,
            request.state.pool,
            user.model_dump(),
            UUID(active_ngroup_id) if active_ngroup_id else None,
            body.status,
            report_request["recipient_email"],
            body.start_date,
            body.end_date,
            base_url=str(request.base_url),
            root_path=request.scope.get("root_path", ""),
        )
        return FileStatusPdfReportResponse(message=report_request["message"], status=body.status)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
