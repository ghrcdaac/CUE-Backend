from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from mangum import Mangum
from dotenv import load_dotenv
from lambda_utils.database_util.db_util import get_connection_pool, setup_connection
import asyncio
from apis.api import router as api_router


load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # List of allowed origins (e.g., your React app)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Routes
# Include the api_router with /v1 prefix
api_version = os.getenv("API_VERSION", "v1")
app.include_router(api_router, prefix=f"/{api_version}")


# Example of using ENV for conditional logic
if os.getenv("ENV") == "production":
    # Do something specific for production
    print("Running in production mode")
    app.debug = False  # Disable debug mode in production
else:
    # Do something else for development/testing
    print("Running in development mode")
    app.debug = True  # Enable debug mode in development



# Initialize the connection pool when the app starts
@app.on_event("startup")
async def startup_event():
    app.state.pool = await get_connection_pool(setup=setup_connection)
    


# Close the connection pool when the app shuts down
@app.on_event("shutdown")
async def shutdown_event():
    await app.state.pool.close()



#Lambda compliance
handler = Mangum(app)


if __name__ == "__main__":
        uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=os.getenv("DEBUG", "false").lower() == "true",
        log_level= "debug"
    )