from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import get_db
from app.core.security.password import hash_password, verify_password
from app.api.routes import auth,cases,documents,meetings,notices,portal,users,recordings
from app.db.session import test_db_connection
from fastapi.middleware.cors import CORSMiddleware
settings = get_settings()
app = FastAPI(title=settings.APP_NAME) 
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite default
        "http://127.0.0.1:5173",
        "https://nms-live.vercel.app",
        "http://localhost:3000"    # If React
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.on_event("startup")
async def startup():
    await test_db_connection()
app.include_router(auth.router)
app.include_router(cases.router)
app.include_router(documents.router)
app.include_router(meetings.router)
app.include_router(notices.router)
app.include_router(portal.router)
app.include_router(recordings.router)
app.include_router(users.router)
@app.get("/test-hash") 
async def test_hash(): 

    pw = "mypassword123" 
    hashed = hash_password(pw) 
    return { "hashed": hashed, "verified": verify_password(pw, hashed), } 

@app.get("/health") 
async def health(db: AsyncSession = Depends(get_db)): 
    result = await db.execute(text("SELECT 1")) 
    return { "status": "ok", "db": result.scalar_one(), }