from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path

router = APIRouter(tags=["Frontend"])
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@router.get("/")
async def get_frontend(request: Request):
    return templates.TemplateResponse(name="index.html", context={"request": request}, request=request)

@router.get("/app")
async def get_app(request: Request):
    return templates.TemplateResponse(name="app.html", context={"request": request}, request=request)
