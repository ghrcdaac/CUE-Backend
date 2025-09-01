import logging
import os
import json
import uuid
import time
import structlog 
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from dotenv import load_dotenv
from starlette.types import ASGIApp, Receive, Scope, Send

# --- Import and set up structured logging at the very top ---
# This ensures all subsequent logs are structured correctly.
# The import path assumes main.py is in 'src/python/api/'.
from core.logging_config import setup_logging
setup_logging()

# --- Use absolute imports for clarity and reliability ---
# These imports are now more explicit based on the new project structure.
from lambda_utils.database_util.db_util import get_connection_pool, setup_connection
from v1.api import router as api_router_v1
from v2.api import router as api_router_v2

# Get a structlog logger instance instead of a standard logger.
logger = structlog.get_logger(__name__)


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
                        # Use the main app logger to log this event
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



# --- Add the request logging middleware ---
# This middleware adds a unique request_id to every log message for easy tracing.
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    # Clear context for each new request
    structlog.contextvars.clear_contextvars()

    # Generate a unique ID for the request
    request_id = str(uuid.uuid4())
    
    # Bind context variables that will be included in all logs for this request
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        http_method=request.method,
        path=request.url.path,
        client_host=request.client.host
    )

    start_time = time.time()
    logger.info("request_started")

    try:
        response = await call_next(request)
        # Add status code to the context for the final log message
        structlog.contextvars.bind_contextvars(status_code=response.status_code)
        return response
    except Exception as e:
        # Log unhandled exceptions before they propagate
        logger.error("unhandled_exception", exc_info=True)
        # Add a 500 status code to the context for the final log message
        structlog.contextvars.bind_contextvars(status_code=500)
        raise e
    finally:
        end_time = time.time()
        duration = (end_time - start_time) * 1000
        logger.info("request_finished", duration_ms=round(duration, 2))


# Apply other middlewares. The order matters.
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

# --- This section is preserved for v1 backward compatibility, remove this when removing v1 ---
@app.on_event("startup")
async def startup_event():
    """Creates the legacy connection pool required by v1 code."""
    logger.info("event.startup.creating_legacy_pool_for_v1")
    app.state.pool = await get_connection_pool(setup=setup_connection)

@app.on_event("shutdown")
async def shutdown_event():
    """Closes the legacy connection pool on shutdown."""
    if hasattr(app.state, 'pool') and app.state.pool:
        logger.info("event.shutdown.closing_legacy_pool")
        await app.state.pool.close()
# -- v1  till here --

# The Mangum handler for running in AWS Lambda
handler = Mangum(app)

# The uvicorn block for local execution
if __name__ == "__main__":
    import uvicorn
    # Use the main app logger to announce the mode
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
