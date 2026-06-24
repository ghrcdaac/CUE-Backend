from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, Request, Header
from uuid import UUID
from typing import Optional

from core.security import get_current_user, require_privilege
from v2.type_util.auth import AuthUser
from v2.utils import report as report_utils
from v2.type_util.report import (
    FileStatusPdfReportRequest,
    FileStatusPdfReportResponse,
)

router = APIRouter(prefix="/reports", tags=["V2 - Reports"])

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
        )
        return FileStatusPdfReportResponse(message=report_request["message"], status=body.status)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
