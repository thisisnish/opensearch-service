from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Specification(BaseModel):
    originalName: str
    values: List[str]
    name: str


class SpecificationGroup(BaseModel):
    originalName: str
    name: str
    specifications: List[Specification]


class SkuSpecificationValue(BaseModel):
    originalName: str
    name: str


class SkuSpecification(BaseModel):
    field: SkuSpecificationValue
    values: List[SkuSpecificationValue]


class Image(BaseModel):
    imageText: str = ""
    imageId: str
    imageLabel: str
    imageUrl: str
    imageTag: Optional[str]
    cacheId: str


class SellerOffer(BaseModel):
    price: float
    name: str
    id: str
    type: str


class CommertialOffer(BaseModel):
    spotPrice: float
    rewardValue: int = Field(..., alias="RewardValue")
    tax: float = Field(..., alias="Tax")
    listPrice: float = Field(..., alias="ListPrice")
    availableQuantity: int = Field(..., alias="AvailableQuantity")
    priceWithoutDiscount: float = Field(..., alias="PriceWithoutDiscount")
    rewardValue: int = Field(..., alias="RewardValue")
    price: float = Field(..., alias="Price")
    isMarkdown: bool = False
    offerings: List[SellerOffer] = []


class Seller(BaseModel):
    sellerId: str
    sellerName: str
    addToCartLink: Optional[str]
    sellerDefault: bool
    commertialOffer: CommertialOffer


class ItemAttribute(BaseModel):
    visible: bool
    name: str
    id: int
    isVisible: bool = None
    value: str


class Variation(BaseModel):
    values: List[str]
    name: str


class Item(BaseModel):
    images: List[Image]
    attachments: List[dict] = []
    unitMultiplier: int
    nameComplete: str
    complementName: Optional[str]
    videos: List[dict] = []
    referenceId: List[dict] = []
    measurementUnit: str
    itemId: str
    isKit: bool
    ean: str = ""
    modalType: str = ""
    variations: List[Variation] = []
    name: str
    attributes: List[ItemAttribute]
    sellers: List[Seller]
    docLastUpdatedBy: str = ""
    docLastUpdatedAt: str = ""


class Product(BaseModel):
    productId: str
    categoriesIds: List[str]
    releaseDate: int
    origin: str
    link: str
    productReference: str
    description: str
    linkText: str
    productName: str
    productClusters: List[dict]
    cacheId: str
    brandId: str
    clusterHighlights: List[dict] = []
    categories: List[str]
    docLastUpdatedBy: str = ""
    brand: str
    specificationGroups: List[SpecificationGroup]
    categoryId: str
    properties: List[Specification]
    skuSpecifications: List[SkuSpecification]
    docLastUpdatedAt: str = ""
    items: List[Item]
    adMetaUi: Optional[Any] = None
