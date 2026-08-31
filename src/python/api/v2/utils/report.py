from typing import Dict, Any, Optional
from datetime import date
from uuid import UUID
from v2.type_util.auth import AuthUser

import boto3
import structlog

logger = structlog.get_logger(__name__)

VALID_FILE_STATUSES = {"unscanned", "clean", "infected", "scan_failed", "distributed"}

async def generate_file_status_pdf_report(
    requesting_user: Dict[str, Any],
    active_ngroup_id: Optional[UUID],
    status: str,
    recipient_email: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    """Triggers the AWS Glue Job to build and email the file status PDF report."""
    logger.info(
        "file.status_pdf_report.triggering_glue",
        status=status,
        recipient=recipient_email,
        requesting_user_id=str(requesting_user.get("id")),
    )

    glue_client = boto3.client("glue")
    
    username = requesting_user.get("cueusername") or requesting_user.get("preferred_username") or requesting_user.get("name") or "Unknown"
    user_roles = requesting_user.get("roles", [])
    roles_str = ",".join(user_roles) if isinstance(user_roles, list) else ""

    try:
        response = glue_client.start_job_run(
            JobName="file_status_report_generator",
            Arguments={
                "--RECIPIENT_EMAIL": recipient_email,
                "--STATUS": status,
                "--START_DATE": start_date.isoformat() if start_date else "none",
                "--END_DATE": end_date.isoformat() if end_date else "none",
                "--ACTIVE_NGROUP_ID": str(active_ngroup_id) if active_ngroup_id else "none",
                "--REQUESTING_USER_ID": str(requesting_user.get("id", "")),
                "--REQUESTING_USER_NAME": username,
                "--REQUESTING_USER_ROLES": roles_str if roles_str else "none",
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
