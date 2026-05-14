from __future__ import annotations

import os

from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from mcp_server import mcp


class BearerAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        expected_token = os.getenv("MCP_BEARER_TOKEN", "dev-token")

        auth_header = request.headers.get("authorization", "")

        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                {"error": "Missing Bearer token"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = auth_header.removeprefix("Bearer ").strip()

        if token != expected_token:
            return JSONResponse(
                {"error": "Invalid Bearer token"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )

        return await call_next(request)


middleware = [
    Middleware(BearerAuthMiddleware),
]

app = mcp.http_app(
    path="/mcp/",
    middleware=middleware,
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
    )