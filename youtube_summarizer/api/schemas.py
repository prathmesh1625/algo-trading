from pydantic import BaseModel, HttpUrl


class AnalyzeRequest(BaseModel):
    url: str


class AnalyzeResponse(BaseModel):
    id: str
    title: str
    channel: str


class ErrorResponse(BaseModel):
    error: str
