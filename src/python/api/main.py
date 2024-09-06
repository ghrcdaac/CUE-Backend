from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from mangum import Mangum
from dotenv import load_dotenv

from api.api import router

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
app.include_router(router, prefix="/api")

#Lambda compliance
handler = Mangum(app)

if __name__ == "__main__":
    uvicorn.run(app, port=8000)