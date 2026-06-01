import logging
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from llm_api.context.app_context import AppContext
from llm_api.routes.routes import create_router
from llm_api.settings.app import get_settings

logging.basicConfig(level=logging.DEBUG)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    await AppContext.initialize(get_settings())
    yield
    await AppContext.close()


app = FastAPI(lifespan=lifespan)

FastAPIInstrumentor.instrument_app(app)

logging.getLogger("opentelemetry").setLevel(logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.DEBUG)

app.include_router(create_router())

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)