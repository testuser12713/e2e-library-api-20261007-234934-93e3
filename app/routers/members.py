"""Member CRUD routes."""

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_api_key
from app.errors import ApiError
from app.models import Member
from app.schemas import MemberCreate, MemberRead, MemberUpdate

router = APIRouter(prefix="/members", tags=["members"])

_DUPLICATE_EMAIL_MESSAGE = "A member with this email already exists"


def _get_member_or_404(db: Session, member_id: int) -> Member:
    """Return the member or raise the uniform 404 error."""

    member = db.get(Member, member_id)
    if member is None:
        raise ApiError(404, "member_not_found", "Member not found")
    return member


def _email_taken(db: Session, email: str, exclude_id: int | None = None) -> bool:
    """Whether another member already uses ``email``."""

    stmt = select(Member.id).where(Member.email == email)
    if exclude_id is not None:
        stmt = stmt.where(Member.id != exclude_id)
    return db.scalar(stmt) is not None


def _commit(db: Session) -> None:
    """Commit, translating a unique-email race into the domain 409."""

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(409, "duplicate_email", _DUPLICATE_EMAIL_MESSAGE) from exc


@router.post("", response_model=MemberRead, status_code=status.HTTP_201_CREATED)
def create_member(
    payload: MemberCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_api_key),
) -> Member:
    """Create a member; a duplicate email is a 409."""

    if _email_taken(db, payload.email):
        raise ApiError(409, "duplicate_email", _DUPLICATE_EMAIL_MESSAGE)

    member = Member(
        name=payload.name,
        email=payload.email,
        member_since=payload.member_since,
    )
    db.add(member)
    _commit(db)
    db.refresh(member)
    return member


@router.get("", response_model=list[MemberRead])
def list_members(db: Session = Depends(get_db)) -> list[Member]:
    """Return every member."""

    return list(db.scalars(select(Member).order_by(Member.id)))


@router.get("/{member_id}", response_model=MemberRead)
def get_member(member_id: int, db: Session = Depends(get_db)) -> Member:
    """Return one member or 404."""

    return _get_member_or_404(db, member_id)


@router.put("/{member_id}", response_model=MemberRead)
def update_member(
    member_id: int,
    payload: MemberUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_api_key),
) -> Member:
    """Replace the provided fields of a member."""

    member = _get_member_or_404(db, member_id)
    _apply_update(db, member, payload)
    return member


@router.patch("/{member_id}", response_model=MemberRead)
def patch_member(
    member_id: int,
    payload: MemberUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_api_key),
) -> Member:
    """Update only the fields present in the request."""

    member = _get_member_or_404(db, member_id)
    _apply_update(db, member, payload)
    return member


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(
    member_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_api_key),
) -> None:
    """Delete a member; a following GET returns 404."""

    member = _get_member_or_404(db, member_id)
    db.delete(member)
    db.commit()


def _apply_update(db: Session, member: Member, payload: MemberUpdate) -> None:
    """Apply the set fields and persist, guarding the unique email."""

    changes = payload.model_dump(exclude_unset=True)

    new_email = changes.get("email")
    if (
        new_email is not None
        and new_email != member.email
        and _email_taken(db, new_email, member.id)
    ):
        raise ApiError(409, "duplicate_email", _DUPLICATE_EMAIL_MESSAGE)

    for field, value in changes.items():
        setattr(member, field, value)

    _commit(db)
    db.refresh(member)
