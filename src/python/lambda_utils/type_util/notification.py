from pydantic import BaseModel
from typing import Tuple
from uuid import UUID
from datetime import datetime

class NotificationReturn(BaseModel):
    id: UUID
    cueuser_id: UUID
    report_type: str
    frequency: str
    created_time: datetime
    updated_time: datetime
    
    @classmethod
    def from_db_row(cls, row: Tuple) -> "NotificationReturn":
        id, cueuser_id, report_type, frequency, created_time, updated_time = row
        return cls(id=id, cueuser_id=cueuser_id, report_type=report_type, frequency=frequency, 
                   created_time=created_time,updated_time=updated_time)
    
class Notification(BaseModel):
    report_type: str
    frequency: str

class NotificationCreate(Notification):
    user_id: UUID

