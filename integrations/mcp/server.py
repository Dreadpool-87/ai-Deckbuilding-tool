"""Optional MCP v2 adapter; requires `pip install 'mcp>=2,<3'`.

Local stdio by default. HTTP is explicitly opt-in and requires bearer auth.
"""
from __future__ import annotations

import argparse
import os
import secrets

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from integrations.mcp.bridge import execute

mcp = MCPServer("AI Deckbuilding Tool")


@mcp.tool()
def discover_cards(collection_csv: str, theme: str, confirmed: bool = False,
                   offline: bool = False) -> dict:
    """Discover OWNED Magic cards with the actual pinned Card Search/Gateway.

    The user must confirm this CSV for the current run. Suggestions are
    heuristics, not validated decks. Never invent cards or execution evidence.
    """
    return execute("discover", collection_csv, theme=theme, confirmed=confirmed,
                   offline=offline)


@mcp.tool()
def validate_deck(collection_csv: str, decklist: str,
                  confirmed: bool = False, offline: bool = False) -> dict:
    """Validate an AI-authored EXACTLY 60-card Casual MTG deck using the pinned CLI.

    Deck lines look like '4 Lightning Bolt'. The user must confirm this CSV.
    VALIDATED_WITH_LIMITATIONS proves only supported structural checks, never
    strategy, full legality, castability, or win rate. If blocked, revise and retry.
    """
    return execute("validate", collection_csv, decklist=decklist,
                   confirmed=confirmed, offline=offline)


class BearerGate:
    """No public unauthenticated access to potentially private collection tools."""

    def __init__(self, app, token: str):
        self.app = app
        self.expected = ("Bearer " + token).encode("ascii")

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        authorization = next((v for k, v in scope.get("headers", [])
                              if k.lower() == b"authorization"), b"")
        if not secrets.compare_digest(authorization, self.expected):
            await send({"type": "http.response.start", "status": 401,
                        "headers": [(b"www-authenticate", b"Bearer"),
                                    (b"content-type", b"text/plain; charset=utf-8")]})
            await send({"type": "http.response.body", "body": b"Unauthorized"})
            return
        await self.app(scope, receive, send)


def http_app(token: str, allowed_hosts: list[str]):
    if len(token) < 32 or not token.isascii():
        raise ValueError("MTG_MCP_TOKEN must be at least 32 ASCII characters")
    if not allowed_hosts or any(not h.strip() for h in allowed_hosts):
        raise ValueError("Explicit MTG_MCP_ALLOWED_HOSTS is required")
    security = TransportSecuritySettings(allowed_hosts=allowed_hosts,
                                         allowed_origins=[])
    inner = mcp.streamable_http_app(stateless_http=True, json_response=True,
                                    max_request_body_size=MAX_BODY,
                                    transport_security=security)
    return BearerGate(inner, token)


MAX_BODY = 4 * 1024 * 1024


def main() -> None:
    parser = argparse.ArgumentParser(description="Minimal MTG MCP tools")
    parser.add_argument("--transport", choices=("stdio", "http"), default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.transport == "stdio":
        mcp.run(transport="stdio")
        return
    token = os.environ.get("MTG_MCP_TOKEN", "")
    hosts = os.environ.get("MTG_MCP_ALLOWED_HOSTS", "127.0.0.1,127.0.0.1:*,localhost,localhost:*")
    app = http_app(token, [h.strip() for h in hosts.split(",")])
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port, access_log=False)


if __name__ == "__main__":
    main()
