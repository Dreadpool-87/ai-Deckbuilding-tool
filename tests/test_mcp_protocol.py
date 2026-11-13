"""Actual MCP protocol smoke. Skipped by default without optional mcp SDK."""
import importlib.util
import unittest


@unittest.skipUnless(importlib.util.find_spec('mcp'), 'Optional MCP SDK is not installed')
class ProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_tools_list_and_confirmation_gate(self):
        from mcp import Client
        from integrations.mcp.server import mcp

        async with Client(mcp) as client:
            tools = await client.list_tools()
            self.assertEqual({tool.name for tool in tools.tools},
                             {'discover_cards', 'validate_deck'})
            result = await client.call_tool('discover_cards', {
                'collection_csv': 'Name,Quantity\nShock,4\n',
                'theme': 'burn',
                'confirmed': False,
            })
            self.assertEqual(result.structured_content['status'], 'UNVERIFIED')
            self.assertIn('CURRENT_RUN_COLLECTION_CONFIRMATION_REQUIRED',
                          result.structured_content['reason_codes'])

    async def test_bearer_gate_denies_unauthenticated_requests(self):
        from integrations.mcp.server import BearerGate
        calls = []

        async def inner(scope, receive, send):
            calls.append('inner')

        gate = BearerGate(inner, 's' * 32)
        response = []

        async def emit(message):
            response.append(message)

        await gate({'type': 'http', 'headers': []}, None, emit)
        self.assertEqual(response[0]['status'], 401)
        self.assertEqual(calls, [])
        await gate({'type': 'http', 'headers': [
            (b'authorization', b'Bearer ' + b's' * 32)]}, None, emit)
        self.assertEqual(calls, ['inner'])


if __name__ == '__main__':
    unittest.main()
