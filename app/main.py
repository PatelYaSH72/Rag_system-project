from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine
from app.core.qdrant import ensure_collection
from app.api.v1.router import api_router

# Import models so Base.metadata knows about them before create_all
from app.models import user, document  # noqa: F401

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.on_event("startup")
def on_startup():
    # Connect to Postgres — creates the "users" table if it doesn't exist
    Base.metadata.create_all(bind=engine)

    # Connect to Qdrant — creates the vector collection if it doesn't exist
    ensure_collection()


@app.get("/health")
def health_check():
    return {"status": "ok"}
