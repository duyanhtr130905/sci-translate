# Placeholder — TV2 sẽ implement
# Pydantic models: TranslateRequest, TranslateResponse
from pydantic import BaseModel


class TranslateRequest(BaseModel):
    text: str


class TranslateResponse(BaseModel):
    input: str
    output: str