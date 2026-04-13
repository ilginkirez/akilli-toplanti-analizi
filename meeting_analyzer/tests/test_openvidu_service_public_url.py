import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = PROJECT_ROOT / "src" / "services" / "openvidu_service.py"


def load_openvidu_service_module():
    fake_httpx = types.ModuleType("httpx")
    fake_httpx.AsyncClient = object

    previous_httpx = sys.modules.get("httpx")
    if previous_httpx is None:
        sys.modules["httpx"] = fake_httpx

    try:
        spec = importlib.util.spec_from_file_location(
            "openvidu_service_under_test",
            MODULE_PATH,
        )
        assert spec is not None and spec.loader is not None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        if previous_httpx is None:
            sys.modules.pop("httpx", None)
        else:
            sys.modules["httpx"] = previous_httpx


def test_create_connection_returns_token_unchanged():
    openvidu_service = load_openvidu_service_module()

    openvidu_service._request = AsyncMock(
        return_value={
            "id": "conn-123",
            "token": "wss://public.example.com?sessionId=test-room&token=tok_123",
        }
    )

    # Exercise the real helper path.
    import asyncio

    payload = asyncio.run(
        openvidu_service.create_connection(
            session_id="test-room",
            participant_id="par_123",
            display_name="Alice",
        )
    )

    assert payload["token"] == "wss://public.example.com?sessionId=test-room&token=tok_123"
