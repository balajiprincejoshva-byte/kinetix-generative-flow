from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.api.routes import router
from backend.config import CORS_ORIGINS
from contextlib import asynccontextmanager
import logging

logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup, initialize and pre-warm the model
    from backend.model.inference import load_or_init_model
    app.state.model = load_or_init_model()
    logging.info("KinetiX model initialized.")
    yield
    # Clean up on shutdown if needed
    pass

app = FastAPI(
    title="KinetiX",
    description="Generative Flow-Matching for Millisecond Protein Dynamics",
    version="0.1.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware, 
    allow_origins=CORS_ORIGINS, 
    allow_methods=["*"], 
    allow_headers=["*"]
)

# Include API router
app.include_router(router, prefix="/api")

# Mount frontend static files
# We use html=True so that / serves index.html
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
