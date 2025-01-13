from dataclasses import dataclass
from enum import Enum


class FacetEnum(Enum):
    BRAND = "brand"
    PRODUCT_TYPE = "product-type"
    PRICE = "price"


class FacetType(Enum):
    TEXT = "TEXT"
    PRICERANGE = "PRICERANGE"


@dataclass
class FacetInfo:
    key_enum: FacetEnum
    name: str
    value_location: str
    slug_location: str | None
    facet_type: FacetType
    is_active: bool

    def key(self):
        return self.key_enum.value

    def aggs_name_facet_value(self):
        return f"{self.key()}-facet"

    def aggs_name_facet_count(self):
        return f"{self.key()}-count"

    def aggs_name_facet_min(self):
        return f"{self.key()}-min"

    def aggs_name_facet_max(self):
        return f"{self.key()}-max"


FACET_METADATA = {
    FacetEnum.BRAND: FacetInfo(
        key_enum=FacetEnum.BRAND,
        name="Brand",
        value_location="searchProductFields.brand.keyword",
        slug_location="searchProductFields.brand-slug.keyword",
        facet_type=FacetType.TEXT,
        is_active=True,
    ),
    FacetEnum.PRODUCT_TYPE: FacetInfo(
        key_enum=FacetEnum.PRODUCT_TYPE,
        name="Category",
        value_location="searchProductFields.productType.keyword",
        slug_location="searchProductFields.product-type-slug.keyword",
        facet_type=FacetType.TEXT,
        is_active=True,
    ),
    FacetEnum.PRICE: FacetInfo(
        key_enum=FacetEnum.PRICE,
        name="Price",
        value_location="searchSellers.commertialOffer.Price",
        slug_location=None,
        facet_type=FacetType.PRICERANGE,
        is_active=True,
    ),
}
