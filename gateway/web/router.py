from fastapi import APIRouter
from fastapi.responses import FileResponse
from pathlib import Path

STATIC_DIR = Path(__file__).parent.parent.parent / "static"

router = APIRouter()


@router.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@router.get("/dashboard")
async def dashboard():
    return FileResponse(STATIC_DIR / "dashboard.html")


@router.get("/style.css")
async def style():
    return FileResponse(STATIC_DIR / "style.css")
