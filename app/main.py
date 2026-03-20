from fastapi import FastAPI
from contextlib import asynccontextmanager
from .database import engine, Base
from .routers import auth, users

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(title="Auth Service", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(users.router)