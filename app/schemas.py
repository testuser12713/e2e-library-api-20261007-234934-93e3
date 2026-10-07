"""Pydantic schemas describing the API request and response bodies."""

from datetime import date

from pydantic import BaseModel, ConfigDict


class BookCreate(BaseModel):
    title: str
    author: str
    isbn: str
    year: int
    copies: int


class BookUpdate(BaseModel):
    title: str | None = None
    author: str | None = None
    isbn: str | None = None
    year: int | None = None
    copies: int | None = None


class BookRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author: str
    isbn: str
    year: int
    copies: int


class BookPage(BaseModel):
    items: list[BookRead]
    total: int
    limit: int
    offset: int


class MemberCreate(BaseModel):
    name: str
    email: str
    member_since: date


class MemberUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    member_since: date | None = None


class MemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    member_since: date


class LoanCreate(BaseModel):
    book_id: int
    member_id: int


class LoanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    member_id: int
    loaned_on: date
    due_on: date
    returned_on: date | None
