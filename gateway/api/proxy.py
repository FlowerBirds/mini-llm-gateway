import json
import logging
import time
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, StreamingResponse, JSONResponse
import httpx

from ..models.manager import get_model_manager
from ..stats.collector import get_stats_collector

logger = logging.getLogger(__name__)
router = APIRouter()


@router.head("/anthropic")
async def head_anthropic():
    return Response(status_code=200)


@router.post("/anthropic/v1/messages/count_tokens")
async def proxy_count_tokens(request: Request):
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    model_key = body.get("model", "")

    model_manager = get_model_manager()
    model_config = model_manager.get_model_by_id(model_key)

    if not model_config:
        model_config = model_manager.get_active_model()

    if not model_config:
        raise HTTPException(status_code=400, detail="No model configured")

    api_key = model_config.get("api_key", "")
    base_url = model_config.get("base_url", "").rstrip("/")

    if not base_url:
        raise HTTPException(status_code=400, detail="Model base_url not configured")

    qp = str(request.query_params)
    upstream_url = f"{base_url}/v1/messages/count_tokens" + (f"?{qp}" if qp else "")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            upstream_response = await client.post(
                upstream_url,
                json=body,
                headers=headers
            )

        if upstream_response.status_code >= 400:
            logger.error(f"Count tokens upstream error {upstream_response.status_code}: {upstream_response.text[:1000]}")
            try:
                error_body = upstream_response.json()
                return JSONResponse(content=error_body, status_code=upstream_response.status_code)
            except Exception:
                return Response(
                    content=upstream_response.text,
                    status_code=upstream_response.status_code,
                    media_type=upstream_response.headers.get("content-type", "text/plain")
                )

        return upstream_response.json()

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Count tokens proxy exception: {type(e).__name__}: {e}")
        error_detail = {"type": "error", "error": {"type": type(e).__name__, "message": str(e)}}
        return JSONResponse(content=error_detail, status_code=502)


def _record(model_id: str, input_tokens: int, output_tokens: int,
            cache_read_tokens: int, cache_creation_tokens: int,
            duration: float, error: bool = False):
    throughput = round(output_tokens / duration, 2) if duration > 0 else 0.0
    get_stats_collector().record_request(
        model_id, input_tokens, output_tokens,
        cache_read_tokens=cache_read_tokens,
        cache_creation_tokens=cache_creation_tokens,
        duration=duration, throughput=throughput, error=error
    )


@router.api_route("/anthropic/v1/messages", methods=["POST"])
async def proxy_messages(request: Request):
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    model_key = body.get("model", "")

    model_manager = get_model_manager()
    model_config = model_manager.get_model_by_id(model_key)

    if not model_config:
        model_config = model_manager.get_active_model()

    if not model_config:
        raise HTTPException(status_code=400, detail="No model configured")

    api_key = model_config.get("api_key", "")
    base_url = model_config.get("base_url", "").rstrip("/")

    if not base_url:
        raise HTTPException(status_code=400, detail="Model base_url not configured")

    upstream_url = f"{base_url}/v1/messages"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    start_time = time.perf_counter()

    try:
        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            upstream_response = await client.post(
                upstream_url,
                json=body,
                headers=headers
            )

        duration = time.perf_counter() - start_time
        logger.info(f"Upstream status: {upstream_response.status_code}, content-type: {upstream_response.headers.get('content-type')}")

        if upstream_response.status_code >= 400:
            logger.error(f"Upstream error {upstream_response.status_code}: {upstream_response.text[:1000]}")
            _record(model_config.get("id", model_key), 0, 0, 0, 0, duration, error=True)
            try:
                error_body = upstream_response.json()
                return JSONResponse(content=error_body, status_code=upstream_response.status_code)
            except Exception:
                return Response(
                    content=upstream_response.text,
                    status_code=upstream_response.status_code,
                    media_type=upstream_response.headers.get("content-type", "text/plain")
                )

        content_type = upstream_response.headers.get("content-type", "")

        if "text/event-stream" in content_type:
            return StreamingResponse(
                content=_sse_generator(upstream_response.text, model_config.get("id", model_key), duration),
                media_type="text/event-stream"
            )

        upstream_data = upstream_response.json()

        usage = upstream_data.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        cache_read_tokens = usage.get("cache_read_input_tokens", 0)
        cache_creation_tokens = usage.get("cache_creation_input_tokens", 0)
        model_id = model_config.get("id", model_key)

        _record(model_id, input_tokens, output_tokens,
                cache_read_tokens, cache_creation_tokens, duration)

        return upstream_data

    except HTTPException:
        raise
    except Exception as e:
        duration = time.perf_counter() - start_time
        logger.exception(f"Proxy exception: {type(e).__name__}: {e}")
        _record(model_config.get("id", model_key), 0, 0, 0, 0, duration, error=True)
        error_detail = {"type": "error", "error": {"type": type(e).__name__, "message": str(e)}}
        return JSONResponse(content=error_detail, status_code=502)


async def _sse_generator(text: str, model_id: str, duration: float):
    lines = text.split("\n")
    buffer = []
    input_tokens = 0
    output_tokens = 0
    cache_read_tokens = 0
    cache_creation_tokens = 0

    for line in lines:
        if line.startswith("data: "):
            data_str = line[6:]
            try:
                data = json.loads(data_str)
                if data.get("type") == "message_delta":
                    usage = data.get("usage", {})
                    input_tokens = usage.get("input_tokens", 0)
                    output_tokens = usage.get("output_tokens", 0)
                    cache_read_tokens = usage.get("cache_read_input_tokens", 0)
                    cache_creation_tokens = usage.get("cache_creation_input_tokens", 0)
            except json.JSONDecodeError:
                pass
        buffer.append(line)
        if line == "":
            yield "\n".join(buffer) + "\n"
            buffer = []

    if buffer:
        yield "\n".join(buffer) + "\n"

    _record(model_id, input_tokens, output_tokens,
            cache_read_tokens, cache_creation_tokens, duration)
