from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from mangum import Mangum
from dotenv import load_dotenv
from lambda_utils.database_util.db_util import get_connection_pool
from apis.api import router

load_dotenv()

root_path = os.getenv('ENV', default='')

app = FastAPI(root_path=f'/{root_path}')

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(router, prefix="/app")

async def startup_event():
    """
    Initialize resources.
    """
    app.state.pool = await get_connection_pool()

async def shutdown_event():
    """
    Gracefully close resources.
    """
    await app.state.pool.close()

app.add_event_handler("startup", startup_event)
app.add_event_handler("shutdown", shutdown_event)


#Lambda compliance
handler = Mangum(app)

if __name__ == "__main__":
    uvicorn.run(app, port=8000)