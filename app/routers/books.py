"""Book routes. Filled in by the book CRUD ticket."""

from fastapi import APIRouter

router = APIRouter(prefix="/books", tags=["books"])
