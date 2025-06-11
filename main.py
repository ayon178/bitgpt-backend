from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.db import connect_to_db
from starlette.staticfiles import StaticFiles
import os

# Routes
from auth.router import router as auth_router
from modules.user.router import router as user_router
from modules.image.router import router as image_router


UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Initialize the FastAPI app
app = FastAPI(title="Tutor", version="0.1.0")

# Connect to the database
connect_to_db()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000"
    ],
    allow_origin_regex=r"http://localhost:\d+",  # Accepts any localhost port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Mount static directory
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/")
async def root():
    return {"message": "Welcome to Bigget API 🔥"}


# Include the routers
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(user_router, prefix="/user", tags=["User"])
app.include_router(image_router, prefix="/image", tags=["Image"])

