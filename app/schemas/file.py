from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    fileRecordId: str
    fileUrl: str
    fileType: str
    originalName: str
    fileSize: int
