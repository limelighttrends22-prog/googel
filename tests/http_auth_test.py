"""Real local ASGI HTTP requests with synthetic configuration; no OAuth login."""

import os
import subprocess
import sys
import textwrap


def test_oauth_http_rejects_anonymous_and_exposes_discovery(tmp_path):
    env = os.environ.copy()
    env.update(
        {
            "GOOGLE_ADS_MCP_OAUTH_CLIENT_ID": "synthetic-client.apps.googleusercontent.com",
            "GOOGLE_ADS_MCP_OAUTH_CLIENT_SECRET": "synthetic-secret-not-a-real-credential",
            "GOOGLE_ADS_MCP_BASE_URL": "https://mcp.example.test",
            "GOOGLE_ADS_MCP_JWT_SIGNING_KEY": "synthetic-test-key-" + "x" * 48,
            "GOOGLE_ADS_MCP_STORAGE_TYPE": "filetree",
            "GOOGLE_ADS_MCP_STORAGE_PATH": str(tmp_path / "oauth"),
            "GOOGLE_ADS_MCP_ALLOWED_REDIRECT_URIS": "https://chatgpt.com/connector/oauth/synthetic",
        }
    )
    code = textwrap.dedent("""
        import asyncio
        import httpx2
        from ads_mcp.server import mcp
        async def main():
            app=mcp.http_app()
            async with app.router.lifespan_context(app):
                async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app),base_url='https://mcp.example.test') as client:
                    response=await client.post('/mcp',json={'jsonrpc':'2.0','id':1,'method':'tools/list'},headers={'Accept':'application/json, text/event-stream'})
                    assert response.status_code==401, (response.status_code,response.text)
                    assert 'resource_metadata' in response.headers.get('www-authenticate','')
                    metadata=await client.get('/.well-known/oauth-authorization-server')
                    assert metadata.status_code==200, metadata.text
                    data=metadata.json()
                    assert 'S256' in data['code_challenge_methods_supported']
                    assert data.get('authorization_response_iss_parameter_supported') is True
                    invalid=await client.post('/mcp',json={'jsonrpc':'2.0','id':1,'method':'tools/list'},headers={'Accept':'application/json, text/event-stream','Authorization':'Bearer synthetic-invalid-token'})
                    assert invalid.status_code==401
            print('anonymous=401 invalid_token=401 metadata=200 pkce=S256 issuer_protection=enabled')
        asyncio.run(main())
    """)
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
