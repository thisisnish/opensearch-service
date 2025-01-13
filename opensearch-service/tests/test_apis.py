from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app
from search.facets_query import FacetsSearchQuery
from search.products_query import ProductsSearchQuery
from search.sku_to_product_id_query import SkuToProductIdQuery

client = TestClient(app)


@patch.object(ProductsSearchQuery, "execute_search")
def test_products_search(mock_os_search):
    mock_os_search.return_value = {}
    response = client.get("/products")
    assert response.status_code == 404

    response = client.get("/products/trade-policy/3")
    assert response.status_code == 200

    response = client.get("/products/foo/trade-policy/3/bar")
    assert response.status_code == 200


@patch.object(SkuToProductIdQuery, "execute_search")
@patch.object(ProductsSearchQuery, "execute_search")
def test_product_detail(mock_sku_search, mock_os_search):
    mock_os_search.return_value = {}
    response = client.get("/product_detail")
    assert response.status_code == 404

    response = client.get("/product_detail/foo/trade-policy/3/bar")
    assert response.status_code == 200


@patch.object(FacetsSearchQuery, "execute_search")
def test_facets_search(mock_facets_search):
    mock_facets_search.return_value = {}
    response = client.get("/facets")
    assert response.status_code == 404

    response = client.get("/facets/foo/trade-policy/3/bar")
    assert response.status_code == 200
