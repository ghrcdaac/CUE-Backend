from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class NotificationResponse(BaseModel):
    id: UUID
    cueuser_id: UUID
    report_type: str
    frequency: str
    created_time: datetime
    updated_time: datetime

    class Config:
        from_attributes = True

class Notification(BaseModel):
    report_type: str
    frequency: str

class NotificationCreate(Notification):
    user_id: UUID