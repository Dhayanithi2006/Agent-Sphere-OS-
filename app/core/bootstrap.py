"""Application bootstrapper and lifecycle manager for AgentSphere OS v4."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import AppSettings, settings as default_settings
from app.core.logging import get_logger, setup_logging
from app.api.health import router as health_router
from app.api.processes import router as processes_router
from app.api.dashboard import router as dashboard_router

from app.core.shared import kernel, process_manager, process_repository, supervisor, event_bus, scheduler, dependency_manager, checkpoint_manager, recovery_engine, model_router, resource_manager, plugin_manager, tool_registry, tool_manager, execution_engine, process_sandbox

logger = get_logger("agentsphere.bootstrap")


class AppBootstrap:
    """Manages configuration, logging, and asynchronous startup/shutdown hooks of the application."""

    def __init__(self, settings: AppSettings = default_settings) -> None:
        self.settings = settings
        # Initialize global structured logging based on injected settings
        setup_logging(self.settings)

        # Reference core subsystems from shared registry
        self.process_repository = process_repository
        self.process_manager = process_manager
        self.kernel = kernel
        self.supervisor = supervisor
        self.event_bus = event_bus
        self.scheduler = scheduler
        self.dependency_manager = dependency_manager
        self.checkpoint_manager = checkpoint_manager
        self.recovery_engine = recovery_engine
        self.model_router = model_router
        self.resource_manager = resource_manager
        self.plugin_manager = plugin_manager
        self.tool_registry = tool_registry
        self.tool_manager = tool_manager
        self.execution_engine = execution_engine
        self.process_sandbox = process_sandbox

    @asynccontextmanager
    async def lifespan(self, app: FastAPI) -> AsyncGenerator[None, None]:
        """Lifecycle hook context manager for starting and stopping microkernel processes."""
        # 1. Startup phase
        logger.info(
            "Booting AgentSphere OS v4 Microkernel...",
            extra={
                "app_name": self.settings.app_name,
                "version": self.settings.app_version,
                "environment": self.settings.environment,
            }
        )
        
        # Start event bus dispatch processing
        await self.event_bus.start()
        
        # Trigger core Microkernel boot
        await self.kernel.boot()
        
        yield

        # 2. Shutdown phase
        logger.info("Gracefully shutting down AgentSphere OS v4 Microkernel...")
        # Shutdown event bus dispatch processing
        await self.event_bus.stop()

    def create_app(self) -> FastAPI:
        """Create, configure, and return the FastAPI application instance."""
        app = FastAPI(
            title=self.settings.app_name,
            version=self.settings.app_version,
            lifespan=self.lifespan,
        )

        # Attach core runtime dependencies to app.state
        app.state.kernel = self.kernel
        app.state.process_manager = self.process_manager
        app.state.supervisor = self.supervisor
        app.state.event_bus = self.event_bus
        app.state.scheduler = self.scheduler
        app.state.dependency_manager = self.dependency_manager
        app.state.checkpoint_manager = self.checkpoint_manager
        app.state.recovery_engine = self.recovery_engine
        app.state.model_router = self.model_router
        app.state.resource_manager = self.resource_manager
        app.state.plugin_manager = self.plugin_manager
        app.state.tool_registry = self.tool_registry
        app.state.tool_manager = self.tool_manager
        app.state.execution_engine = self.execution_engine
        app.state.process_sandbox = self.process_sandbox

        # Standard CORS setup
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Wire up core routers
        app.include_router(health_router)
        app.include_router(processes_router)
        app.include_router(dashboard_router)

        @app.get("/favicon.ico", include_in_schema=False)
        def favicon():
            from fastapi import Response
            return Response(status_code=204)

        # Mount static files (dashboard UI and media assets) and serve dashboard route
        from fastapi.staticfiles import StaticFiles
        from fastapi.responses import FileResponse
        import os
        
        static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))
        if os.path.exists(static_dir):
            app.mount("/static", StaticFiles(directory=static_dir), name="static")

            # Ensure workspace dir exists so generated files are always serveable
            workspace_dir = os.path.join(static_dir, "workspace")
            os.makedirs(workspace_dir, exist_ok=True)
            
            @app.get("/dashboard", include_in_schema=False)
            def serve_dashboard():
                return FileResponse(os.path.join(static_dir, "dashboard.html"))
                
            logger.info("Static files mounted and /dashboard endpoint registered successfully.")

        # Wire up legacy/other routes gracefully if present
        try:
            from app.api.routes import router as core_router
            app.include_router(core_router)
            logger.info("Legacy runtime routers loaded successfully")
        except ImportError as exc:
            logger.warning(f"Could not load legacy routes: {exc}")

        return app
