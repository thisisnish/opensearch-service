import unittest

from search.AdSearch.util import inject_ads


class TestInjectAds(unittest.TestCase):
    def setUp(self):
        self.organic_products = [
            {
                "id": "123",
                "name": "book",
            },
            {
                "id": "456",
                "name": "pen",
            },
            {"id": "789", "name": "pencil"},
        ]

    def test_inject_ad_skip_when_no_products(self):
        ad_products = []
        result = inject_ads(self.organic_products, ad_products)
        self.assertEqual(result, self.organic_products)

    def test_inject_ad_skip_when_no_metadata(self):
        ad_products = [{"key", "value"}]
        result = inject_ads(self.organic_products, ad_products)
        self.assertEqual(result, self.organic_products)

    def test_inject_ad_when_inside_bound(self):
        organic_product_count = len(self.organic_products)
        ad_products = [
            {
                "adMetaBackend": {"position": 0, "ifMoreThan": 2},
                "skuInfo": {
                    "productResult": {"id": "111", "name": "ad"},
                    "productSkuResult": {
                        "item": {
                            "itemId": "12345",
                            "attachments": [],
                            "images": [{"imageId": "123"}],
                        }
                    },
                    "offerItemResult": {
                        "sellers": [
                            {
                                "sellerId": "1",
                            }
                        ]
                    },
                },
                "adMetaUi": None,
            }
        ]
        expected_ad_product = {
            "adMetaUi": None,
            "id": "111",
            "name": "ad",
            "items": [
                {
                    "images": [{"imageId": "123"}],
                    "itemId": "12345",
                    "attachments": [],
                    "sellers": [{"sellerId": "1"}],
                }
            ],
        }
        result = inject_ads(self.organic_products, ad_products)
        self.assertEqual(result[0], expected_ad_product)
        self.assertEqual(len(self.organic_products), organic_product_count + 1)

    def test_inject_ad_when_outside_bound(self):
        organic_product_count = len(self.organic_products)
        ad_products = [
            {
                "adMetaBackend": {"position": 0, "ifMoreThan": 4},
                "skuInfo": {"productResult": {"id": "111", "name": "ad"}},
                "adMetaUi": None,
            }
        ]
        result = inject_ads(self.organic_products, ad_products)
        self.assertEqual(len(self.organic_products), organic_product_count)
