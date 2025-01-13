import asyncio
import os
from contextlib import asynccontextmanager

import newrelic.agent
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import UJSONResponse
from opensearchpy import TransportError
from pydantic_core._pydantic_core import ValidationError
from structlog.contextvars import bind_contextvars, clear_contextvars

from auth.bearer_token_auth import TokenBearer
from constants.logging import (
    MESSAGE_INTERNAL_SERVICE_ERROR,
    REQUEST_TYPE_FACETS,
    REQUEST_TYPE_PRODUCT_DETAIL,
    REQUEST_TYPE_PRODUCT_SEARCH,
)
from converter.facets_response import os_to_vtex_facets_response
from converter.products_response import os_to_vtex_products_response
from converter.sku_to_product_id_response import os_sku_to_product_id
from middleware import check_for_required_path_params, extract_traceparent_header
from pulse.publish import pulse_pdp_quantities
from schemas.api import FacetsResponseModel, ProductsResponseModel, SelectedFacet
from search.AdSearch.error import AdSearchError
from search.AdSearch.http import AdHttpService, check_metadata_exists
from search.AdSearch.util import inject_ads
from search.base_products_query import BaseProductQuery
from search.facets_query import FacetsSearchQuery
from search.products_query import ProductsSearchQuery
from search.sku_to_product_id_query import SkuToProductIdQuery
from util.envvar import (
    AD_SERVICE_ENABLED,
    NEW_RELIC_CONFIG_FILE,
    OPEN_SEARCH_HOST,
    PRODUCTS_INDEX,
    STAGE,
)
from util.logging import (
    get_logger,
    log_record_for_ads_error,
    log_record_for_os_error,
    log_record_for_schema_validation_error,
    log_record_for_transport_error,
)
from util.metrics import record_metric
from util.time import current_milli_time
from util.util import extract_trace_id_from_traceparent, generate_hex_string


def prologue():
    #    newrelic.agent.initialize(os.environ["NEW_RELIC_CONFIG_FILE"])
    return


def epilogue():
    return


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    prologue()
    # Handoff to App
    yield
    # Clean up
    epilogue()


newrelic.agent.initialize(NEW_RELIC_CONFIG_FILE)
log = get_logger("app")
app = FastAPI(lifespan=lifespan)
token_bearer_auth = TokenBearer()

QUERY_SKU_PREFIX = "sku:"
QUERY_PRODUCT_PREFIX = "product:"


@app.middleware("http")
async def incoming_requests_handler(request: Request, call_next):
    try:
        clear_contextvars()
        start_time = current_milli_time()
        success = await check_for_required_path_params(request)
        traceparent = await extract_traceparent_header(request)
        trace_id = extract_trace_id_from_traceparent(traceparent)
        if trace_id is None:
            log.info(
                "Missing trace-id (32hex) in incoming request header. Generating random 32hex trace-id"
            )
            trace_id = generate_hex_string(32)
        request.state.request_id = trace_id
        bind_contextvars(stage=STAGE, trace_id=trace_id, pid=os.getpid())
        response = await call_next(request)
        process_time = current_milli_time() - start_time
        response.headers["traceparent"] = traceparent
        middleware_log = {
            "method": request.method,
            "url": str(request.url),
            "response_time": process_time,
        }
        log.info(middleware_log)
        return response
    except HTTPException as e:
        return UJSONResponse(status_code=e.status_code, content=e.detail)
    except Exception as e:
        return UJSONResponse(status_code=500, content=str(e))


@app.get("/", dependencies=[Depends(token_bearer_auth)])
async def root():
    return {
        "stage": STAGE,
        "products_index": PRODUCTS_INDEX,
        "os_host": OPEN_SEARCH_HOST,
    }


@app.get("/ping")
async def ping():
    return {"message": "PONG"}


@app.get(
    "/products/{param_path:path}",
)
async def product_search(
    request: Request,
    param_path: str,
    page: int = 1,
    count: int = 10,
    query: str = "",
    price: str = "",
    sort: str = "asc",
    fuzzy: str = "0",
    locale: str = "en-US",
    hideUnavailableItems: bool = True,
    validate: bool = False,
):
    start = current_milli_time()
    trade_policy = None
    rmn_call_success = 1

    # os handler call
    async def fetch_os_products():
        nonlocal trade_policy
        psq = (
            ProductsSearchQuery(PRODUCTS_INDEX)
            .page_size(count)
            .page_number(page)
            .exclude_out_of_stock()  # exclude OOS skus for PLP (not PDP)
        )

        psq = parameter_processor(
            psq,
            param_path,
            page,
            count,
            query,
            price,
            sort,
            fuzzy,
            locale,
            hideUnavailableItems,
        )
        trade_policy = psq.get_trade_policy()
        try:
            os_response = psq.execute_search()
        except TransportError as e:
            log.error(log_record_for_transport_error(e, REQUEST_TYPE_PRODUCT_SEARCH))
            raise HTTPException(status_code=500, detail="Internal Service Error")
        except Exception as e:
            log.error(log_record_for_os_error(e, REQUEST_TYPE_PRODUCT_SEARCH))
            raise HTTPException(status_code=500, detail="Internal Service Error")

        request_params = {"page": page, "count": count, "query": query, "fuzzy": fuzzy}
        return os_to_vtex_products_response(request_params, os_response)

    # rmn handler call
    async def fetch_ad_products():
        nonlocal rmn_call_success
        route = request.url.path + "?" + request.url.query
        no_ads = (
            request.query_params.get("no_ads", "") == "y"
            or request.headers.get("x-no-ads", "") == "y"
            or request.headers.get("x-referer", "").find("no_ads=y") > -1
        )

        log_ads_enabled = {
            "AD_SERVICE_ENABLED": AD_SERVICE_ENABLED,
            "no_ads": no_ads,
            "x-no-ads": request.headers.get("x-no-ads"),
            "query_params_no_ads": request.query_params.get("no_ads"),
            "x-ref-no-ads": request.headers.get("x-referer", "").find("no_ads=y") > -1,
        }
        log.info(log_ads_enabled)
        if AD_SERVICE_ENABLED and not no_ads:
            headers = {}
            forwarding_header_keys = [
                "x-original-forwarded-for",
            ]
            for key in request.headers:
                if key in forwarding_header_keys or (
                    isinstance(key, str) and key.startswith("x-vtexcustomer-")
                ):
                    headers[key] = request.headers.get(key)

            try:
                start_ads = current_milli_time()
                ads_response = AdHttpService().get_ads(
                    trace_id=request.state.request_id,
                    headers=headers,
                    params={"search_url": route},
                )
                end_ads = current_milli_time()
                nr_ads_log = {
                    "rmn_latency": end_ads - start_ads,
                    "ad_products_found": len(ads_response.get("products", [])),
                }
                log.info(nr_ads_log)
                return ads_response
            except AdSearchError as e:
                # log error and return OS response without Ads
                rmn_call_success = 0
                log.error(log_record_for_ads_error(e, REQUEST_TYPE_PRODUCT_SEARCH))

    def merge_response():
        if ads_response is None:
            return os_response
        if "products" in os_response and "products" in ads_response:
            # ingest ads products into organic products result
            os_response["products"] = inject_ads(
                os_response["products"], ads_response["products"]
            )
            # add meta data information
            if check_metadata_exists(ads_response["adMetaPlacementUi"]):
                os_response["adMetaPlacementUi"] = ads_response["adMetaPlacementUi"]
        return os_response

    # metrics
    async def ingest_metrics():
        pre_injecting_ads_products_count = len(os_response.get("products", []))
        ad_products_found = len(ads_response.get("products", [])) if ads_response else 0
        products = (
            response.products
            if isinstance(response, ProductsResponseModel)
            else response.get("products", [])
        )
        post_injecting_ads_products_count = len(products)
        ad_products_served = (
            post_injecting_ads_products_count - pre_injecting_ads_products_count
        )
        record_metric("ad_products_found", ad_products_found)
        record_metric("ad_products_served", ad_products_served)
        record_metric("rmn_requests_made", 1)
        record_metric("rmn_call_success", rmn_call_success)

    # fetch os and ads response
    os_response, ads_response = await asyncio.gather(
        fetch_os_products(), fetch_ad_products()
    )
    response = merge_response()
    # ingest metrics in bg and cont processing response
    asyncio.create_task(ingest_metrics())
    # schema response
    try:
        validated_response = ProductsResponseModel(**response)
        if validate:
            response = validated_response
    except ValidationError as e:
        log.error(
            log_record_for_schema_validation_error(e, REQUEST_TYPE_PRODUCT_SEARCH)
        )

    end = current_milli_time()
    products_count = (
        response.recordsFiltered
        if isinstance(response, ProductsResponseModel)
        else response.get("recordsFiltered") if response else 0
    )
    nr_log = {
        "latency": end - start,
        "request_type": REQUEST_TYPE_PRODUCT_SEARCH,
        "product_count": products_count,
        "route": request.url.path + "?" + request.url.query,
        "query": query,
        "trade_policy": trade_policy,
        "validate": validate,
    }
    log.info(nr_log)

    return response


@app.get("/product_detail/{param_path:path}")
async def product_detail(
    request: Request,
    param_path: str,
    query: str = "",
    locale: str = "en-US",
    hideUnavailableItems: bool = True,
):
    start = current_milli_time()
    product_id_list = []

    psq = ProductsSearchQuery(PRODUCTS_INDEX).page_number(1)
    psq = parameter_processor(psq, param_path)
    trade_policy = psq.get_trade_policy()

    # If the query string starts with "sku:" assume FastStore wants all the product details for those sku ids
    # including sibling skus under the same parent.  Because the OS data is organized by sku id, we can't
    # directly get all siblings by just the sku id.  So, first fetch the product ids for those sku ids,
    # then proceed with the rest of the query, passing the product id list as the main filter.
    if query.startswith(QUERY_SKU_PREFIX):
        # TODO: Add a cache
        spq = SkuToProductIdQuery(PRODUCTS_INDEX)

        spq.trade_policy(trade_policy)
        query_sku_ids = query[len(QUERY_SKU_PREFIX) :].split(";")
        spq.sku_id_list(query_sku_ids)
        spq_response = spq.execute_search()
        product_id_list = os_sku_to_product_id(spq_response)
        if len(product_id_list) > len(query_sku_ids):
            nr_log = {
                "request_type": REQUEST_TYPE_PRODUCT_DETAIL,
                "route": request.url.path + "?" + request.url.query,
                "sku_ids": query_sku_ids,
                "product_ids": product_id_list,
                "event": "MULTIPLE_PRODUCT_FOR_SKU",
            }
            log.warn(nr_log)

    # If we have product ids, use those instead of a link_text query
    if len(product_id_list) > 0:
        psq.product_ids(product_id_list).page_size(len(product_id_list))
    else:
        psq.link_text(query.split(";")).page_size(len(query.split(";")))

    try:
        os_response = psq.execute_search()
    except TransportError as e:
        log.error(log_record_for_transport_error(e, REQUEST_TYPE_PRODUCT_DETAIL))
        raise HTTPException(status_code=500, detail="Internal Service Error")
    except Exception as e:
        log.error(log_record_for_os_error(e, REQUEST_TYPE_PRODUCT_DETAIL))
        raise HTTPException(status_code=500, detail="Internal Service Error")

    request_params = {"page": 1, "count": 1, "query": query}
    response = os_to_vtex_products_response(request_params, os_response)
    pulse_pdp_quantities(response, query, psq.get_trade_policy(), request)
    end = current_milli_time()
    nr_log = {
        "latency": end - start,
        "request_type": REQUEST_TYPE_PRODUCT_DETAIL,
        "route": request.url.path + "?" + request.url.query,
    }
    log.info(nr_log)

    try:
        validated_response = ProductsResponseModel(**response)
    except ValidationError as e:
        log.error(
            log_record_for_schema_validation_error(e, REQUEST_TYPE_PRODUCT_DETAIL)
        )

    return response


@app.get("/facets/{param_path:path}")
async def facet_search(
    request: Request,
    param_path: str,
    page: int = 1,
    count: int = 1,
    query: str = "",
    price: str = "",
    sort: str = "asc",
    fuzzy: str = "auto",
    locale: str = "en-US",
    hideUnavailableItems: bool = True,
):
    start = current_milli_time()

    fsq = FacetsSearchQuery(PRODUCTS_INDEX).page_size(count).page_number(page)

    fsq = parameter_processor(
        fsq,
        param_path,
        page,
        count,
        query,
        price,
        sort,
        fuzzy,
        locale,
        hideUnavailableItems,
    )

    try:
        os_response = fsq.execute_search()
    except TransportError as e:
        log.error(log_record_for_transport_error(e, REQUEST_TYPE_FACETS))
        raise HTTPException(status_code=500, detail="Internal Service Error")
    except Exception as e:
        log.error(log_record_for_os_error(e, REQUEST_TYPE_FACETS))
        raise HTTPException(status_code=500, detail="Internal Service Error")

    request_params = {
        "page": page,
        "count": count,
        "query": query,
        "trade_policy": fsq.get_trade_policy(),
    }
    response = os_to_vtex_facets_response(request_params, os_response)
    end = current_milli_time()
    nr_log = {
        "latency": end - start,
        "request_type": REQUEST_TYPE_FACETS,
        "route": request.url.path + "?" + request.url.query,
    }
    log.info(nr_log)

    try:
        validated_response = FacetsResponseModel(**response)
    except ValidationError as e:
        log.error(log_record_for_schema_validation_error(e, REQUEST_TYPE_FACETS))

    return response


def parameter_processor(
    query_builder: BaseProductQuery,
    param_path: str,
    page: int = 1,
    count: int = 10,
    query: str = "",
    price: str = "",
    sort: str = "asc",
    fuzzy: str = "auto",
    locale: str = "en-US",
    hideUnavailableItems: bool = True,
):
    path_array = param_path.split("/")

    if query.startswith(QUERY_SKU_PREFIX):
        query_sku_ids = query[len(QUERY_SKU_PREFIX) :].split(";")
        query_builder.sku_ids(query_sku_ids)
    elif query.startswith(QUERY_PRODUCT_PREFIX):
        query_product_ids = query[len(QUERY_PRODUCT_PREFIX) :].split(";")
        query_builder.product_ids(query_product_ids)
    else:
        query_builder.text_query(query.lower())

    if len(sort) > 0:
        query_builder.sort(sort)

    if len(path_array) > 1:
        path_array_iter = iter(path_array)
        for key in path_array_iter:
            # safety check for odd-length arrays
            value = next(path_array_iter, None)
            if value is not None:
                key_lower = key.lower()
                match key_lower:
                    case "brand":
                        query_builder.brand(value)
                    case "trade-policy":
                        query_builder.trade_policy(value)
                    case "product-type":
                        query_builder.product_type(value)
                    case "productclusterids":
                        query_builder.product_cluster_id(value)
                    case "price":
                        # if price is a path param, override the query param
                        price = value
                    case "ismarkdown":
                        if value == "true":
                            query_builder.include_markdown_only()
                    case "sellerid":
                        query_builder.sellers(value)
                    case _:
                        if key_lower.startswith("category-"):
                            query_builder.category(key, value)

    if len(price) > 0:
        price_range_str = []
        # FastStore customer-facing URLs use "-to-" as price range delimiter
        # Intelligent Search queries seem to use ":" instead
        # Support both until we get enough data to verify usage patterns for both
        if price.find(":") >= 0:
            price_range_str = price.split(":")
        elif price.find("-to-") >= 0:
            price_range_str = price.split("-to-")

        if (
            len(price_range_str) == 2
            and is_float(price_range_str[0])
            and is_float(price_range_str[1])
        ):
            price_range = [float(val) for val in price_range_str]
            query_builder.price_range(price_range[0], price_range[1])

    return query_builder


def is_float(f):
    try:
        float(f)
        return True
    except ValueError:
        return False
