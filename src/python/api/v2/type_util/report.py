from pydantic import BaseModel, Field
from typing import Optional
from datetime import date

class FileStatusPdfReportRequest(BaseModel):
    status: str = Field(..., description="File status to include in the report.")
    start_date: Optional[date] = Field(None, description="Filter for files uploaded on or after this date (YYYY-MM-DD).")
    end_date: Optional[date] = Field(None, description="Filter for files uploaded on or before this date (YYYY-MM-DD).")

class FileStatusPdfReportResponse(BaseModel):
    message: str
    status: str
