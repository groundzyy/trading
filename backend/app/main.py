from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import auth, stocks, signals, decision, watchlist, scanner
from .database import engine, Base

app = FastAPI(title="Trading Signal API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


app.include_router(auth.router)
app.include_router(stocks.router)
app.include_router(signals.router)
app.include_router(decision.router)
app.include_router(watchlist.router)
app.include_router(scanner.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
