from pydantic import BaseModel
from typing import List, Any
from uuid import UUID 

class FilePayload(BaseModel):
    """File Payload for Manual Trigger Event Lambdas"""
    file_ids: List[UUID]

class FileTransferResponse(BaseModel):
    """File Transfer Response from Manual File Transfer Event Lambda"""
    status_code: int
    body: dict[str,Any]