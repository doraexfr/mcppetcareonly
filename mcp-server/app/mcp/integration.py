from fastapi import FastAPI

from app.mcp.fastmcp_server import create_fastmcp_server


def create_mcp_mount(path: str = "/"):
    mcp_server = create_fastmcp_server()
    mcp_http_app = mcp_server.http_app(path=path)
    return mcp_server, mcp_http_app


def mount_mcp_server(app: FastAPI, mount_path: str = "/mcp-server", path: str = "/") -> FastAPI:
    mcp_server, mcp_http_app = create_mcp_mount(path=path)
    app.mount(mount_path, mcp_http_app)
    app.state.mcp_server = mcp_server
    return app
