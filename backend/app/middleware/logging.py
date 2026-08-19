import time
import json
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from loguru import logger

async def set_body(request: Request, body: bytes):
    async def receive():
        return {"type": "http.request", "body": body}
    request._receive = receive

async def get_body(request: Request) -> bytes:
    body = await request.body()
    await set_body(request, body)
    return body

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = getattr(request.state, "request_id", "unknown")
        
        # Read Request Body
        req_body = b""
        try:
            req_body = await get_body(request)
        except Exception as e:
            logger.warning(f"Could not read request body: {e}")

        logger.info(f"Request started: {request.method} {request.url.path} (ID: {request_id})")
        
        if req_body:
            try:
                parsed_body = json.loads(req_body.decode("utf-8"))
                logger.info(f"Request Input: {json.dumps(parsed_body)} (ID: {request_id})")
            except Exception:
                logger.info(f"Request Input (raw): {req_body.decode('utf-8', errors='replace')} (ID: {request_id})")
                
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Read Response Body (call_next always returns StreamingResponse in BaseHTTPMiddleware)
        res_body = b""
        try:
            if hasattr(response, "body_iterator"):
                async for chunk in response.body_iterator:
                    res_body += chunk if isinstance(chunk, bytes) else chunk.encode("utf-8")
                
                # Reconstruct the response iterator
                async def new_body_iterator():
                    yield res_body
                
                response.body_iterator = new_body_iterator()
        except Exception as e:
            logger.warning(f"Could not read response body: {e}")

        if res_body:
            try:
                parsed_res = json.loads(res_body.decode("utf-8"))
                logger.info(f"Response Output: {json.dumps(parsed_res)} (ID: {request_id})")
            except Exception:
                if len(res_body) < 2000:
                    logger.info(f"Response Output (raw): {res_body.decode('utf-8', errors='replace')} (ID: {request_id})")
                else:
                    logger.info(f"Response Output: <Binary/Large data: {len(res_body)} bytes> (ID: {request_id})")

        logger.info(f"Request completed: {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.4f}s (ID: {request_id})")
        
        response.headers["X-Process-Time"] = str(process_time)
        return response
