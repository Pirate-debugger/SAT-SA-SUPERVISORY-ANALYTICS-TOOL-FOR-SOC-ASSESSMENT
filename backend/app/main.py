from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import APP_NAME, APP_VERSION
from app.database import engine, Base
import app.models  # Ensure all models are registered with Base
from app.api.router import api_router

# Create database tables automatically
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Supervisory Analytics Tool for SOC Assessment (SIH26157) - Air-gapped Offline Platform"
)

# Enable CORS for frontend Vite dev server (and local origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/")
def root():
    return {
        "service": APP_NAME,
        "version": APP_VERSION,
        "status": "OPERATIONAL",
        "mode": "AIR_GAPPED_OFFLINE",
        "docs_url": "/docs",
        "api_prefix": "/api"
    }


@app.get("/health")
@app.get("/api/health")
def health_check():
    return {"status": "HEALTHY", "mode": "AIR_GAPPED_OFFLINE_LOCAL"}
