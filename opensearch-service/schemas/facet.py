from typing import List, Optional

from pydantic import BaseModel, Field


class Range(BaseModel):
    from_: Optional[float] = Field(..., alias="from")
    to: Optional[float] = Field(..., alias="to")


class FacetValue(BaseModel):
    id: Optional[str] = ""
    quantity: int
    name: Optional[str] = ""
    key: str
    value: Optional[str] = None
    selected: bool
    href: Optional[str] = None
    range: Optional[Range] = None


class Facet(BaseModel):
    values: List[FacetValue]
    type: str
    name: str
    hidden: bool
    key: str
    quantity: int
