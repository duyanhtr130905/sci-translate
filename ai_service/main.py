import sys
import os
from pathlib import Path

current_dir = Path(__file__).parent.absolute()
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from dotenv import load_dotenv
load_dotenv()
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from api.routes.health import router as health_router
from api.routes.translate import router as translate_router
from api.routes.terms import router as terms_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        print("Warmup skipped (optional chain not enforced)")
    except Exception as e:
        print(f"Ollama warm-up skipped/failed: {e}")
    yield


app = FastAPI(
    title="SCI Translate AI Service",
    version="1.0.0",
    description="Scientific Translation Backend powered by RAG + Ollama",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(translate_router)
app.include_router(terms_router)


@app.get("/")
def root():
    return {
        "service": "SCI Translate AI Service",
        "status": "running",
        "version": "1.0.0"
    }