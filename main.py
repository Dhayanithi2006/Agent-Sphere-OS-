"""Application entrypoint for AgentSphere OS v4 Microkernel."""

from __future__ import annotations

from app.core.bootstrap import AppBootstrap
from app.core.config import settings

if __name__ != "__main__":
    # Initialize runtime environment and build FastAPI instance
    bootstrapper = AppBootstrap(settings)
    app = bootstrapper.create_app()
else:
    app = None

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development",
    )
