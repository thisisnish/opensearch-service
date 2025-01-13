from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from schemas.facet import Facet
from schemas.product import Product


class PageIndex(BaseModel):
    index: int


class Pagination(BaseModel):
    count: int
    current: PageIndex
    before: List
    after: List
    perPage: int
    next: PageIndex
    previous: Union[PageIndex, Dict]
    first: PageIndex
    last: Optional[PageIndex]


class ProductsResponseModel(BaseModel):
    recordsFiltered: int
    pagination: Pagination
    options: Optional[Any] = None
    products: List[Product]
    sampling: bool
    translated: bool
    locale: str
    query: str
    operator: str
    fuzzy: str
    adMetaPlacementUi: Optional[Any] = None

    class Config:
        title = "ProductsResponseModel"
        exclude_none = True
        validate_assignment = True

    def dict(self, *args, **kwargs):
        data = super().dict(*args, **kwargs)
        return {k: v for k, v in data.items() if v is not None and v != [] or v != ""}


class SelectedFacet(BaseModel):
    key: Optional[str] = None
    value: Optional[str] = None


class QueryArgs(BaseModel):
    query: Optional[str] = ""
    selectedFacets: List[SelectedFacet] = []


class FacetsResponseModel(BaseModel):
    facets: List[Facet]
    sampling: bool
    breadcrumb: List[Any]
    queryArgs: QueryArgs
    translated: bool

    class Config:
        title = "FacetsResponseModel"
        exclude_none = True
        validate_assignment = True

    def dict(self, *args, **kwargs):
        data = super().dict(*args, **kwargs)
        return {k: v for k, v in data.items() if v is not None and v != [] or v != ""}
