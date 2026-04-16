import importlib.util
from pathlib import Path

from livekit import api


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = PROJECT_ROOT / "src" / "services" / "livekit_service.py"


def load_livekit_service_module():
    spec = importlib.util.spec_from_file_location(
        "livekit_service_under_test",
        MODULE_PATH,
    )
    assert spec is not None and spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_public_ws_url_uses_ws_scheme(monkeypatch):
    monkeypatch.setenv("LIVEKIT_API_URL", "http://livekit:7880")
    monkeypatch.delenv("LIVEKIT_WS_URL", raising=False)

    service = load_livekit_service_module()
    assert service.public_ws_url() == "ws://livekit:7880"


def test_create_access_token_contains_room_grants(monkeypatch):
    monkeypatch.setenv("LIVEKIT_API_URL", "http://livekit:7880")
    monkeypatch.setenv("LIVEKIT_WS_URL", "wss://rtc.example.com")
    monkeypatch.setenv("LIVEKIT_API_KEY", "testkey")
    monkeypatch.setenv(
        "LIVEKIT_API_SECRET",
        "this_is_a_long_enough_test_secret_for_hs256",
    )

    service = load_livekit_service_module()

    token = service.create_access_token(
        room_name="demo-room",
        participant_id="par_123",
        display_name="Alice",
        metadata={"display_name": "Alice"},
    )
    claims = api.TokenVerifier(
        api_key="testkey",
        api_secret="this_is_a_long_enough_test_secret_for_hs256",
    ).verify(token)

    assert claims.identity == "par_123"
    assert claims.name == "Alice"
    assert claims.video.room_join is True
    assert claims.video.room == "demo-room"
