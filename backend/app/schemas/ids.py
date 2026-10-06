"""Bounded id types. Database ids are positive and fit a MySQL INT, so anything else is a 422,
never a database error (an id like 2**63 would otherwise overflow the driver)."""
from typing import Annotated

from fastapi import Path, Query
from pydantic import Field

MAX_ID = 2_147_483_647

PathId = Annotated[int, Path(ge=1, le=MAX_ID)]
QueryId = Annotated[int | None, Query(ge=1, le=MAX_ID)]
BodyId = Annotated[int, Field(ge=1, le=MAX_ID)]
