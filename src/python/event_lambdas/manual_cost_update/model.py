from pydantic import BaseModel, model_validator
from datetime import datetime
from typing import Optional
from uuid import UUID

class TimeRange(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    user_id: UUID 

    @model_validator(mode='after')
    def validate_time_range(self):
        start_time = self.start_time
        end_time = self.end_time
        
        if start_time and end_time:
            if start_time >= end_time:
                raise ValueError(
                    "start_time must be earlier than end_time"
                )
        return self
