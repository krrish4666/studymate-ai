from pydantic import BaseModel


class ExportPdfRequest(BaseModel):
    feature: str
    outputText: str | None = None
    outputJson: dict | None = None
