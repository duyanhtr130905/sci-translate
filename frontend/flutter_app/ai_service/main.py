from fastapi import FastAPI
from pydantic import BaseModel
import os

app = FastAPI(title="SCI-Translate AI Service")

class HealthResponse(BaseModel):
    status: str
    version: str

@app.get("/health", response_model=HealthResponse)
async def health():
    return {
        "status": "healthy",
        "version": "0.1.0"
    }

@app.get("/")
async def root():
    return {"message": "SCI-Translate AI Service running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
