from pydantic import BaseModel
from typing import Optional, Tuple

class NotificationReturn(BaseModel):
    @classmethod
    def from_db_row(cls, row: Tuple) -> "Notification":
        notification = row[0]  # Adjust according to your table structure
        return cls(notification=notification)
    
class Notification(BaseModel):
    report_type: str
    frequency: str

class NotificationCreate(Notification):
    user_id: int

