"""Book routes: CRUD with search and pagination."""

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_api_key
from app.errors import ApiError
from app.models import Book
from app.schemas import BookCreate, BookPage, BookRead, BookUpdate

router = APIRouter(prefix="/books", tags=["books"])

_DEFAULT_LIMIT = 20
_MAX_LIMIT = 100


def _get_book_or_404(db: Session, book_id: int) -> Book:
    """Load a book by id or raise the uniform 404."""

    book = db.get(Book, book_id)
    if book is None:
        raise ApiError(404, "not_found", f"Book {book_id} not found")
    return book


def _ensure_unique_isbn(db: Session, isbn: str, exclude_id: int | None = None) -> None:
    """Reject an ISBN already claimed by another book."""

    statement = select(Book.id).where(Book.isbn == isbn)
    if exclude_id is not None:
        statement = statement.where(Book.id != exclude_id)
    if db.scalar(statement) is not None:
        raise ApiError(409, "conflict", f"ISBN '{isbn}' is already in use")


def _commit_book(db: Session, book: Book) -> None:
    """Commit a write, mapping a unique-constraint race onto the 409 error."""

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(409, "conflict", "ISBN already in use") from exc
    db.refresh(book)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=BookRead)
def create_book(
    payload: BookCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_api_key),
) -> Book:
    """Create a book; 409 when the ISBN is already taken."""

    _ensure_unique_isbn(db, payload.isbn)
    book = Book(
        title=payload.title,
        author=payload.author,
        isbn=payload.isbn,
        year=payload.year,
        copies=payload.copies,
    )
    db.add(book)
    _commit_book(db, book)
    return book


@router.get("", response_model=BookPage)
def list_books(
    q: str | None = Query(default=None),
    limit: int = Query(default=_DEFAULT_LIMIT, ge=1, le=_MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> BookPage:
    """List books, optionally filtered by a title/author substring."""

    statement = select(Book)
    if q:
        pattern = f"%{q}%"
        statement = statement.where(or_(Book.title.ilike(pattern), Book.author.ilike(pattern)))

    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    items = list(db.scalars(statement.order_by(Book.id).limit(limit).offset(offset)).all())
    return BookPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/{book_id}", response_model=BookRead)
def get_book(book_id: int, db: Session = Depends(get_db)) -> Book:
    """Return one book or the uniform 404."""

    return _get_book_or_404(db, book_id)


@router.put("/{book_id}", response_model=BookRead)
def update_book(
    book_id: int,
    payload: BookUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_api_key),
) -> Book:
    """Update a book; 404 unknown id, 409 duplicate ISBN."""

    book = _get_book_or_404(db, book_id)
    changes = payload.model_dump(exclude_unset=True)
    if "isbn" in changes:
        _ensure_unique_isbn(db, changes["isbn"], exclude_id=book_id)
    for field, value in changes.items():
        setattr(book, field, value)
    _commit_book(db, book)
    return book


@router.patch("/{book_id}", response_model=BookRead)
def patch_book(
    book_id: int,
    payload: BookUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_api_key),
) -> Book:
    """Partially update a book; 404 unknown id, 409 duplicate ISBN."""

    book = _get_book_or_404(db, book_id)
    changes = payload.model_dump(exclude_unset=True)
    if "isbn" in changes:
        _ensure_unique_isbn(db, changes["isbn"], exclude_id=book_id)
    for field, value in changes.items():
        setattr(book, field, value)
    _commit_book(db, book)
    return book


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(
    book_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_api_key),
) -> Response:
    """Delete a book; a later GET answers 404."""

    book = _get_book_or_404(db, book_id)
    db.delete(book)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
