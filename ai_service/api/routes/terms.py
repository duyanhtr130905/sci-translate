# Placeholder — TV2 sẽ implement
# GET /terms/lookup, POST /terms/normalize
from fastapi import APIRouter

router = APIRouter(
    prefix="/terms",
    tags=["terms"]
)

@router.get("/")
def get_terms():

    return {
        "terms": [
            {
                "en": "machine learning",
                "vi": "học máy"
            },
            {
                "en": "deep learning",
                "vi": "học sâu"
            },
            {
                "en": "transformer",
                "vi": "mô hình biến áp"
            }
        ]
    }