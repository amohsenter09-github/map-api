from fastapi import APIRouter, HTTPException

from app.db.session import ping_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/ready")
async def ready():
    try:
        await ping_db()
    except Exception as e:
        raise HTTPException(status_code=503, detail="Database unavailable") from e
    return {"status": "ok", "database": "up"}
