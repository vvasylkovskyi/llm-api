import logging
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from llm_api.context.app_context import AppContext
from llm_api.routes.routes import create_router
from llm_api.settings.app import get_settings

logging.basicConfig(level=logging.DEBUG)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    AppContext.initialize(app, get_settings())
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(create_router())

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)