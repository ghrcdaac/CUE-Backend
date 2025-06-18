import logging
import os
import json
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from dotenv import load_dotenv
from lambda_utils.database_util.db_util import get_connection_pool, setup_connection
from apis.api import router as api_router
from starlette.types import ASGIApp, Receive, Scope, Send

# Configure logging
logging.basicConfig(level=logging.DEBUG if os.getenv("DEBUG", "false").lower() == "true" else logging.INFO)
logger = logging.getLogger(__name__)


class ManualJSONBodyParsingMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Create a new receive channel that will replace the original
        async def new_receive() -> dict:
            message = await receive()
            # We are interested in the message that has the request body
            if message["type"] == "http.request" and message.get("body"):
                body_bytes = message["body"]
                try:
                    # Attempt to decode the body as UTF-8
                    body_str = body_bytes.decode("utf-8")
                    # The body from API Gateway is often a JSON string *within* a JSON payload.
                    # We load it to get the raw string, then load it *again* if it's stringified JSON.
                    data = json.loads(body_str)
                    if isinstance(data, dict) and "body" in data and isinstance(data["body"], str):
                        # This is the key part: we parse the stringified inner 'body'
                        logger.debug("Middleware: Found stringified JSON in body. Parsing.")
                        parsed_inner_body = json.loads(data["body"])
                        # Replace the body with the correctly parsed dictionary
                        message["body"] = json.dumps(parsed_inner_body).encode("utf-8")
                except (json.JSONDecodeError, UnicodeDecodeError):
                    # If it's not valid JSON or can't be decoded, pass it through as-is.
                    logger.debug("Middleware: Body is not a stringified JSON. Passing through.")
                    pass
            return message

        await self.app(scope, new_receive, send)


load_dotenv()

app = FastAPI(
    title="CUE API",
    debug=os.getenv("DEBUG", "false").lower() == "true"
)

# Apply middlewares
# The JSON parsing middleware must be added BEFORE the CORS middleware.
app.add_middleware(ManualJSONBodyParsingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the API router
api_version = os.getenv("API_VERSION", "v1")
app.include_router(api_router, prefix=f"/{api_version}")

if os.getenv("ENV") == "production":
    logger.info("Running in production mode")
else:
    logger.info("Running in development mode")

@app.on_event("startup")
async def startup_event():
    app.state.pool = await get_connection_pool(setup=setup_connection)

@app.on_event("shutdown")
async def shutdown_event():
    await app.state.pool.close()

# The Mangum handler remains the same
handler = Mangum(app)

# The uvicorn block for local execution remains the same
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=os.getenv("DEBUG", "false").lower() == "true",
        log_level="debug"
    )
