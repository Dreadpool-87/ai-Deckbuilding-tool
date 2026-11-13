# Experimental MCP adapter — AI Deckbuilding Tool

This adapter exposes **two tools** to any MCP-compatible client: `discover_cards`
and `validate_deck`. It uses the existing, SHA-pinned Python CLI. It contains no AI
model, ranking logic, new card rules or duplicated Validator.

**Status:** local synthetic adapter tests pass. Cross-agent interoperability,
remote hosting, MTGJSON live setup and Android client acceptance are **not verified**.
MCP compatibility depends on each AI app/plan; publishing a GitHub repository does
not make an MCP server run or make any app support MCP.

## Start (Python 3.12/3.13, full repository checkout)

```sh
python -m pip install -r integrations/mcp/requirements.txt
python -m integrations.mcp.server --transport stdio
```

`stdio` is for a tool-enabled agent on the same computer as the server. From a
compatible AI host, register the command above with the working directory set to
the repository root. It is **not** an Android endpoint.

For Android clients that can connect to remote MCP servers, you must separately
host this process on a server. Use Streamable HTTP behind a trusted HTTPS reverse
proxy and configure an authentication token and allowed hostname:

```sh
# Example only; set a randomly generated secret at least 32 ASCII characters long.
export MTG_MCP_TOKEN='<your secret from a secret manager>'
export MTG_MCP_ALLOWED_HOSTS='mcp.example.org,mcp.example.org:*'
python -m integrations.mcp.server --transport http --host 127.0.0.1 --port 8000
```

Your reverse proxy must terminate HTTPS, restrict access to the backend, and send
requests to `http://127.0.0.1:8000/mcp`. The MCP client must support sending
`Authorization: Bearer <token>` and connect to `https://mcp.example.org/mcp`.
The hostname and URL are **placeholders**, not a deployed service. For containers,
configure networking securely; never publish port 8000 directly to the internet.
The server denies missing/incorrect tokens with HTTP 401; it also checks the HTTP
Host header. Treat the shared token as a secret. This MVP is single-user only:
no accounts, tenant isolation, rate limits or OAuth are provided.

## How an AI should use the tools

1. Ask the user for a current collection export (`Name,Quantity` or supported
   Delver Lens CSV/TSV). Only set `confirmed=true` if the user confirmed this CSV
   for the current run. The flag is a declaration, not cryptographic proof.
2. Call `discover_cards(collection_csv, theme, confirmed=true)` and read the
   returned Gateway evidence and bounded candidate suggestions.
3. **The AI** chooses all cards, quantities, strategy and manabase, then calls
   `validate_deck(collection_csv, decklist, confirmed=true)` with a list such
   as `4 Shock` on each line. If rejected, revise and validate again.
4. Report real tool statuses, never fabricated execution. `VALIDATED_WITH_LIMITATIONS`
   covers only supported structural checks. It does not prove a strong deck,
   complete card legality, castability, gameplay or a win rate.

The tools use temporary private files (removed after each request). They do **not**
commit or upload collections to GitHub. A remote MCP server and the AI client
nevertheless receive the collection: use only trusted services and get the user's
consent before sending their data. The full AtomicCards dataset is downloaded and
verified by the existing CLI on first use. Set `offline=true` only if this server
already has a verified cache. No local Python or installation on the Android phone
is necessary **once an actual remote server is hosted and the AI app supports MCP**.

Limits: collection at most 4 MiB, deck at most 256 KiB, CLI at most 240 seconds.
Free chat-app context limits may still prevent forwarding very large collections.

## Tests

```sh
python -m unittest discover -s tests -p 'test_mcp_bridge.py' -v
```

These unit tests mock the CLI process and verify error handling, private temp
cleanup, response contracts and correct handling of failure. They **do not** prove
an MCP client connection, a live Oracle download, a successful end-to-end deck,
or Android compatibility. Follow up with a real SDK/client acceptance test before
any public deployment.
