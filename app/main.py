from fastapi import FastAPI, UploadFile, File, Query, HTTPException
from fastapi.responses import StreamingResponse, PlainTextResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os
import sys
from .engine import QREngine
from .ui_template import HTML_CONTENT
from .config import load_config

def get_resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("QRServer")

# Load config
config_data = load_config()
enable_docs = config_data.get("enable_api_docs", False)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine
    # Look for models locally (useful for --onedir PyInstaller)
    if getattr(sys, 'frozen', False):
        # In --onedir mode, models should be placed inside _internal/app/models
        base_path = os.path.join(os.path.dirname(sys.executable), "_internal")
        model_path = os.path.join(base_path, "app", "models")
    else:
        model_path = get_resource_path("app/models")
    
    if not os.path.exists(model_path):
        model_path = os.path.abspath(os.path.join(os.getcwd(), "app", "models"))
    
    engine = QREngine(model_path)
    logger.info(f"QR Server initialized. Models: {model_path}")
    yield

app = FastAPI(
    title="QR Code API",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs" if enable_docs else None,
    redoc_url="/redoc" if enable_docs else None,
    openapi_url="/openapi.json" if enable_docs else None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = None

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTML_CONTENT

@app.post("/scan", response_class=PlainTextResponse)
async def scan(file: UploadFile = File(...)):
    MAX_SIZE = config_data.get("max_file_size_mb", 10) * 1024 * 1024
    if file.size and file.size > MAX_SIZE:
        raise HTTPException(status_code=400, detail="File too large")
    
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="File too large")

    if engine:
        result = await engine.decode(content)
        if result and result.get("status") == "success":
            return result.get("data")
        else:
            msg = result.get("message", "No QR found") if result else "No QR found"
            raise HTTPException(status_code=400, detail=msg)
    
    raise HTTPException(status_code=500, detail="Engine not initialized")

@app.get("/generate", responses={200: {"content": {"image/png": {}}}})
async def generate_qr_code(
    content: str = Query(..., max_length=2048),
    size: int = Query(10, ge=1, le=40),
    border: int = Query(4, ge=0, le=10)
):
    if engine:
        img_buffer = engine.generate_qr(content, box_size=size, border=border)
        return StreamingResponse(img_buffer, media_type="image/png")
    raise HTTPException(status_code=500, detail="Engine not initialized")
