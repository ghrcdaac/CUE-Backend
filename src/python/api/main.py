import logging
import os
import json
import uuid
import time
import structlog
import traceback
import asyncio
import asyncpg
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from dotenv import load_dotenv
from starlette.types import ASGIApp, Receive, Scope, Send

# --- X-RAY SDK IMPORTS ---
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch

# --- Patch libraries for X-Ray ---
patch(('httpx', 'boto3', 'requests'))

# --- Import and set up structured logging at the very top ---
from core.logging_config import setup_logging
setup_logging()

# --- Use absolute imports for clarity and reliability ---
from v1.api import router as api_router_v1
from v2.api import router as api_router_v2

# Get a structlog logger instance instead of a standard logger.
logger = structlog.get_logger(__name__)

# --- Global variable for the connection pool ---
# This will hold the connection pool for the lifetime of the Lambda container.
db_pool = None

# --- MODIFIED: Function to initialize the database pool using v2 config ---
async def initialize_database_pool():
    """
    Initializes a global asyncpg connection pool using v2 environment variables.
    This pool is created once per Lambda container and reused across invocations.
    """
    global db_pool
    if db_pool is None:
        logger.info("db.pool.initializing_for_v2")
        try:
            db_pool = await asyncpg.create_pool(
                host=os.getenv("PG_HOST"),
                port=os.getenv("PG_PORT", 5432),
                database=os.getenv("PG_DB"),
                user=os.getenv("PG_USER"),
                password=os.getenv("PG_PASS"),
                ssl=os.getenv("DB_SSL_MODE", "require"),
                min_size=1, # Ensure at least one connection is kept warm
                max_size=10
            )
            # "Ping" the database to establish a real connection during init
            async with db_pool.acquire() as connection:
                await connection.fetchval('SELECT 1')
            logger.info("db.pool.initialized_successfully")
        except Exception as e:
            logger.error("db.pool.initialization_failed", exc_info=True)
            raise e

# --- Run the database initialization in the global scope ---
try:
    logger.info("lambda.init.start")
    asyncio.run(initialize_database_pool())
    logger.info("lambda.init.finish")
except Exception as e:
    logger.error("lambda.init.failed", exc_info=True)
    raise e


class ManualJSONBodyParsingMiddleware:
    """This middleware correctly handles double-serialized JSON from API Gateway."""
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def new_receive() -> dict:
            message = await receive()
            if message["type"] == "http.request" and message.get("body"):
                body_bytes = message["body"]
                try:
                    body_str = body_bytes.decode("utf-8")
                    data = json.loads(body_str)
                    if isinstance(data, dict) and "body" in data and isinstance(data["body"], str):
                        logger.debug("middleware.json_parser.body.found_stringified")
                        parsed_inner_body = json.loads(data["body"])
                        message["body"] = json.dumps(parsed_inner_body).encode("utf-8")
                except (json.JSONDecodeError, UnicodeDecodeError):
                    logger.debug("middleware.json_parser.body.not_stringified")
                    pass
            return message

        await self.app(scope, new_receive, send)


load_dotenv()

API_ROOT_PATH = os.getenv("API_ROOT_PATH", "")

app = FastAPI(
    title="CUE API",
    openapi_version="3.1.0",
    root_path=API_ROOT_PATH,
    debug=os.getenv("DEBUG", "false").lower() == "true"
)

# --- MIDDLEWARE: Combined X-Ray and Logging ---
@app.middleware("http")
async def xray_and_logging_middleware(request: Request, call_next):
    segment = xray_recorder.begin_segment(name=f"fastapi-app.{request.url.path}")
    segment.put_http_meta('url', str(request.url))
    segment.put_http_meta('method', request.method)
    
    structlog.contextvars.clear_contextvars()
    request_id = str(uuid.uuid4())
    
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        trace_id=segment.trace_id,
        http_method=request.method,
        path=request.url.path,
        client_host=request.client.host
    )
    
    # Attach the global pool to the request state for v2 handlers
    request.state.pool = db_pool

    start_time = time.time()
    logger.info("request_started")

    try:
        response = await call_next(request)
        structlog.contextvars.bind_contextvars(status_code=response.status_code)
        segment.put_http_meta('status', response.status_code)
        return response
    except Exception as e:
        logger.error("unhandled_exception", exc_info=True)
        structlog.contextvars.bind_contextvars(status_code=500)
        segment.put_http_meta('status', 500)
        segment.add_exception(e, traceback.extract_stack())
        raise e
    finally:
        end_time = time.time()
        duration = (end_time - start_time) * 1000
        logger.info("request_finished", duration_ms=round(duration, 2))
        xray_recorder.end_segment()


# Apply other middlewares
app.add_middleware(ManualJSONBodyParsingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the versioned API routers
app.include_router(api_router_v1, prefix="/v1", tags=["v1"])
app.include_router(api_router_v2, prefix="/v2", tags=["v2"])

# --- Restored startup/shutdown events for v1 compatibility ---
@app.on_event("startup")
async def startup_event():
    """Assigns the pre-warmed global pool to app.state for v1 code."""
    logger.info("event.startup.assigning_pool_for_v1")
    app.state.pool = db_pool

@app.on_event("shutdown")
async def shutdown_event():
    """Logs shutdown, but does not close the global pool."""
    logger.info("event.shutdown.not_closing_global_pool")


# The Mangum handler for running in AWS Lambda
handler = Mangum(app)

# The uvicorn block for local execution
if __name__ == "__main__":
    import uvicorn
    if os.getenv("ENV") == "production":
        logger.info("main.startup.mode.production")
    else:
        logger.info("main.startup.mode.development")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=os.getenv("DEBUG", "false").lower() == "true",
        log_level="debug"
    )

