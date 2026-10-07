"""Loan return routes.

Included before the loans router so that the static ``/loans/overdue`` path is
matched before the dynamic ``/loans/{loan_id}`` path.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/loans", tags=["loans"])
