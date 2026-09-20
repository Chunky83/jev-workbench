"""Send a real MCP proposal into an isolated native UI smoke-test workspace."""
import asyncio
import json
import sys

# Applies the same embedded-Windows runtime bootstrap as the shipped connector.
from jev_diagnostics.connectors import mcp_server  # noqa: F401
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def send(launcher, case_id):
    parameters = StdioServerParameters(command=launcher['command'], args=launcher['args'],
                                      env=launcher.get('env'))
    async with stdio_client(parameters) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()

            async def call(name, arguments):
                response = await session.call_tool(name, arguments)
                if response.isError:
                    raise RuntimeError('MCP tool rejected ' + name)
                return response.structuredContent

            before = await call('read_case', {'case_id': case_id})
            evidence_ids = [item['id'] for item in before['evidence']]
            if not evidence_ids:
                raise AssertionError('Prepared sample must have synthetic evidence')
            submitted = await call('submit_proposal', {
                'case_id': case_id, 'expected_revision': before['case']['revision'],
                'summary': 'Incoming Claude proposal for the first saved sample',
                'evidence_ids': evidence_ids, 'check_id': 'guest_access_fixture',
                'expected_result': 'Guest denied with HTTP 401 and no protected content; owner permitted.'})
            after = await call('read_case', {'case_id': case_id})
            assert after['case']['revision'] == submitted['revision']
            assert after['case']['snapshot'] == before['case']['snapshot']
            return {'case_id': case_id, 'proposal_id': submitted['proposal']['id'],
                    'revision': submitted['revision']}


if __name__ == '__main__':
    result = asyncio.run(asyncio.wait_for(send(json.loads(sys.argv[1]), sys.argv[2]), 25))
    print(json.dumps(result))
