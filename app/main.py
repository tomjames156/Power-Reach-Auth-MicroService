from fastapi import FastAPI
from contextlib import asynccontextmanager
from .routers import auth, users
import subprocess

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up Power Reach Auth Service...")
    yield
    print("Shutting down...")

app = FastAPI(title="Auth Service", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(users.router)