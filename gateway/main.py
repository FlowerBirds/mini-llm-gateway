from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .config import get_config
from .api import proxy, models, admin
from .web.router import router as web_router


def create_app() -> FastAPI:
    config = get_config()

    app = FastAPI(title="Mini LLM Gateway", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(web_router)
    app.include_router(proxy.router)
    app.include_router(models.router)
    app.include_router(admin.router)

    return app


app = create_app()


if __name__ == "__main__":
    config = get_config()
    uvicorn.run(
        "gateway.main:app",
        host=config.host,
        port=config.port,
        reload=False
    )
