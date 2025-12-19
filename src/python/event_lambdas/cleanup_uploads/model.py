from pydantic import BaseModel, Field, model_validator
from typing import Optional,Literal
from uuid import UUID 
from datetime import date

class QueryParameters(BaseModel):
    #Optional query parameters
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    user_id: Optional[UUID] = None
    collection_id: Optional[UUID] = None
    provider_id: Optional[UUID] = None

class CleanupPayload(BaseModel):
    detail_type: Literal["CleanupAllPendingUploads", "CleanupTargetedUploads"] = Field(..., alias="detail-type")
    query_parameters: Optional[QueryParameters] = None

    @model_validator(mode="after")
    def validate_payload(self) -> "CleanupPayload":
        if self.detail_type not in ("CleanupAllPendingUploads", "CleanupTargetedUploads"):
            raise ValueError('detail-type must be either "CleanupAllPendingUploads" or "CleanupTargetedUploads"')
        if self.detail_type == "CleanupTargetedUploads":
            field_list = "start_date", "end_date", "user_id", "collection_id", "provider_id"
            if self.query_parameters is None:
                raise ValueError('"query_parameters" is missing when detail-type is "CleanupTargetedUploads"')
            else:
                if all(getattr(self.query_parameters, field) is None for field in field_list):
                    raise ValueError('At least 1 query parameter must be used when detail-type is "CleanupTargetedUploads"')

        return self
