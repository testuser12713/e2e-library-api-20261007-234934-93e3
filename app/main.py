"""FastAPI application entry point for the city library lending API."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import init_db
from app.errors import register_exception_handlers
from app.routers import books, loan_returns, loans, members


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create the database schema on startup."""

    init_db()
    yield


app = FastAPI(title="Stadtbibliothek-Ausleih-API", lifespan=lifespan)

register_exception_handlers(app)

app.include_router(books.router)
app.include_router(members.router)
app.include_router(loan_returns.router)
app.include_router(loans.router)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe."""

    return {"status": "ok"}
