# Placeholder — TV2 sẽ implement
# TermLookupRequest, TermResponse
from pydantic import BaseModel


class TermRequest(BaseModel):
    term: str


class TermResponse(BaseModel):
    term: str
    translations: list