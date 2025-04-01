from typing import Optional
from pydantic import BaseModel, PositiveInt


class upload_url_pld(BaseModel):
    file_name: str
    checksum: str
    size: PositiveInt
    collection: str
    file_type: str
    collection_path: Optional[str] = None
    
class upload_url_return(BaseModel):
    url: str
    fields: dict