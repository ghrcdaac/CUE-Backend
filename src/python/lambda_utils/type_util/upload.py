from pydantic import BaseModel, PositiveInt, Base64Str


class upload_url_pld(BaseModel):
    file_name: str
    checksum: Base64Str
    size: PositiveInt
    collection: str
    daac: str
    
class upload_url_return(BaseModel):
    url: str
    fields: dict