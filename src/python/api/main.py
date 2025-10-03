"""
Main application file for the CUE API.
Handles application startup, middleware, and router inclusion.
This version uses a modern 'lifespan' context manager, loads security keys from
a local file, and has environment-aware X-Ray tracing.
"""
import os
import sys
import json
import uuid
import time
from contextlib import asynccontextmanager

import asyncpg
import httpx
import structlog
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from dotenv import load_dotenv
from starlette.types import ASGIApp, Receive, Scope, Send

from core.logging_config import setup_logging
from core import security as security_utils
from v1.api import router as api_router_v1
from v2.api import router as api_router_v2


IS_LOCAL_ENVIRONMENT = os.getenv("XRAY_LOCAL_FLAG_NAME", False)

if IS_LOCAL_ENVIRONMENT:
    # --- This block runs ONLY LOCALLY ---
    print(f"INFO: X-Ray tracing is DISABLED ('{IS_LOCAL_ENVIRONMENT}' flag is set).")
    class DummyXRayRecorder:
        def begin_segment(self, *args, **kwargs): pass
        def end_segment(self, *args, **kwargs): pass
        def begin_subsegment(self, *args, **kwargs): return self
        def end_subsegment(self, *args, **kwargs): pass
        def put_metadata(self, *args, **kwargs): pass
        def put_annotation(self, *args, **kwargs): pass
        def add_exception(self, *args, **kwargs): pass
        def current_segment(self): return None
    xray_recorder = DummyXRayRecorder()
else:
    # --- This block runs in AWS Lambda  ---
    print("INFO: X-Ray tracing is ENABLED")
    from aws_xray_sdk.core import xray_recorder, patch
    patch(('httpx', 'boto3', 'requests'))

# --- Initial Setup ---
setup_logging()
logger = structlog.get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the application's lifecycle for startup and shutdown events.
    """
    # --- Startup Logic ---
    logger.info("event.lifespan.startup.begin")
    start_time = time.time()

    # 1. Initialize Database Pool
    db_init_start = time.time()
    logger.info("db.pool.initializing")
    try:
        db_host = os.getenv("PG_HOST")
        db_port = os.getenv("PG_PORT", 5432)
        db_name = os.getenv("PG_DB")
        db_user = os.getenv("PG_USER")
        db_pass = os.getenv("PG_PASS")
        if not all([db_host, db_name, db_user, db_pass]):
            raise ValueError("One or more required database environment variables are not set.")
        app.state.pool = await asyncpg.create_pool(
            host=db_host, port=db_port, database=db_name, user=db_user, password=db_pass,
            ssl=os.getenv("DB_SSL_MODE", "require"),
            min_size=int(os.getenv("POOL_MIN_SIZE", "1")),
            max_size=int(os.getenv("POOL_MAX_SIZE", "10")),
            timeout=8
        )
        logger.info("db.pool.initialized_successfully", duration_ms=round((time.time() - db_init_start) * 1000, 2))
    except Exception:
        logger.critical("db.pool.initialization_failed", exc_info=True)
        app.state.pool = None

    # 2. Initialize Shared HTTP Client
    http_init_start = time.time()
    logger.info("http.client.initializing")
    try:
        app.state.http_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=10.0))
        logger.info("http.client.initialized_successfully", duration_ms=round((time.time() - http_init_start) * 1000, 2))
    except Exception:
        logger.critical("http.client.initialization_failed", exc_info=True)
        app.state.http_client = None

    # 3. Initialize JWKS by loading from local file
    jwks_init_start = time.time()
    logger.info("jwks.initializing_from_file")
    try:
        app.state.jwks_keys = security_utils.load_jwks_from_file()
        logger.info("jwks.initialized_successfully_from_file", duration_ms=round((time.time() - jwks_init_start) * 1000, 2))
    except Exception as e:
        logger.critical("jwks.initialization_failed_fatal", error=str(e))
        app.state.jwks_keys = None

    logger.info("event.lifespan.startup.finished", total_duration_ms=round((time.time() - start_time) * 1000, 2))
    yield
    # --- Shutdown Logic ---
    logger.info("event.lifespan.shutdown.begin")
    if getattr(app.state, 'pool', None):
        await app.state.pool.close()
        logger.info("db.pool.closed")
    if getattr(app.state, 'http_client', None) and not app.state.http_client.is_closed:
        await app.state.http_client.aclose()
        logger.info("http.client.closed")
    logger.info("event.lifespan.shutdown.finished")

load_dotenv()
API_ROOT_PATH = os.getenv("API_ROOT_PATH", "")

app = FastAPI(
    title="CUE API",
    openapi_version="3.1.0",
    root_path=API_ROOT_PATH,
    debug=os.getenv("DEBUG", "false").lower() == "true",
    lifespan=lifespan
)

class ManualJSONBodyParsingMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app
    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        async def new_receive() -> dict:
            message = await receive()
            if message["type"] == "http.request" and message.get("body"):
                try:
                    body_str = message["body"].decode("utf-8")
                    data = json.loads(body_str)
                    if isinstance(data, dict) and "body" in data and isinstance(data["body"], str):
                        parsed_inner_body = json.loads(data["body"])
                        message["body"] = json.dumps(parsed_inner_body).encode("utf-8")
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
            return message
        await self.app(scope, new_receive, send)

@app.middleware("http")
async def xray_and_logging_middleware(request: Request, call_next):
    structlog.contextvars.clear_contextvars()
    xray_trace_id = request.headers.get("x-amzn-trace-id")
    request_id = str(uuid.uuid4())
    structlog.contextvars.bind_contextvars(request_id=request_id, xray_trace_id=xray_trace_id)
    
    # Health checks for services initialized during startup
    if not getattr(request.app.state, "pool", None):
        logger.critical("db.pool.not_available_for_request.returning_503")
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"detail": "Service unavailable: Database connection pool failed."})
    if not getattr(request.app.state, "http_client", None):
        logger.critical("http.client.not_available_for_request.returning_503")
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"detail": "Service unavailable: HTTP client failed to initialize."})
    if not getattr(request.app.state, "jwks_keys", None):
        logger.critical("jwks.not_available_for_request.returning_503")
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"detail": "Service unavailable: Security keys failed to load."})

    request.state.pool = request.app.state.pool
    start_time = time.time()
    logger.info("request_started", path=request.url.path, method=request.method)
    
    response = None
    subsegment = xray_recorder.begin_subsegment('application_logic')
    try:
        subsegment.put_metadata('http', {"request": {"url": str(request.url), "method": request.method}})
        subsegment.put_annotation("request_id", request_id)
        
        response = await call_next(request)
        
        subsegment.put_metadata('http.response', {"status_code": response.status_code})
        return response
    except Exception as e:
        subsegment.add_exception(e, sys.exc_info())
        logger.error("unhandled_exception", exc_info=True)
        raise e
    finally:
        duration = (time.time() - start_time) * 1000
        status_code = response.status_code if response else 500
        logger.info("request_finished", duration_ms=round(duration, 2), status_code=status_code)
        xray_recorder.end_subsegment()

app.add_middleware(ManualJSONBodyParsingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# app.include_router(api_router_v1, prefix="/v1", tags=["v1"])
app.include_router(api_router_v2, prefix="/v2", tags=["v2"])

handler = Mangum(app)

# The uvicorn block for local execution
if __name__ == "__main__":
    import uvicorn
    if os.getenv("ENV") == "production":
        logger.info("main.startup.mode.production")
    else:
        logger.info("main.startup.mode.development")
    uvicorn.run(
        "main:app", host="0.0.0.0", port=8000,
        reload=os.getenv("DEBUG", "false").lower() == "true",
        log_level="debug"
    )