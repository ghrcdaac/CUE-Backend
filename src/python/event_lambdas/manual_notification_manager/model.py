from pydantic import BaseModel, model_validator, Field
from uuid import UUID 


class Notification(BaseModel):
    detail_type: str = Field(..., alias="detail-type")
    detail: dict 
    user_id: UUID

    @model_validator(mode="after")
    def check_detail_type(self):
        if self.detail_type == "InfectedFileFound":
            if "key" not in self.detail:
                raise ValueError("key missing from detail")
            try:
                UUID(self.detail["key"])
            except:
                raise ValueError("key is not a UUID") 
        elif self.detail_type == "ScheduledInfectedFileFound":
            pass 
        elif self.detail_type == "UserApplicationSubmitted":
            if "application_id" not in self.detail:
                raise ValueError("application_id is missing from detail")
            try:
                UUID(self.detail["application_id"])
            except:
                raise ValueError("application_id is not a UUID") 

        elif self.detail_type == "UserApplicationApproved":
            if "user_id" not in self.detail:
                raise ValueError("user_id is missing from detail")
            try:
                UUID(self.detail["user_id"])
            except:
                raise ValueError("user_id is not a UUID") 
        else:
            raise ValueError("Invalid detail_type")
        return self 