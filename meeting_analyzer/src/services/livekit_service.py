from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, Optional

try:
    from google.protobuf.json_format import MessageToDict
    from livekit import api
    LIVEKIT_IMPORT_ERROR: ModuleNotFoundError | None = None
except ModuleNotFoundError as exc:
    MessageToDict = None
    api = None
    LIVEKIT_IMPORT_ERROR = exc


LIVEKIT_API_URL = os.getenv("LIVEKIT_API_URL", "http://livekit:7880").rstrip("/")
LIVEKIT_WS_URL = os.getenv("LIVEKIT_WS_URL", "").rstrip("/")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")
LIVEKIT_ROOM_EMPTY_TIMEOUT = int(os.getenv("LIVEKIT_ROOM_EMPTY_TIMEOUT", "300"))
LIVEKIT_ROOM_DEPARTURE_TIMEOUT = int(os.getenv("LIVEKIT_ROOM_DEPARTURE_TIMEOUT", "20"))
LIVEKIT_ROOM_MAX_PARTICIPANTS = int(os.getenv("LIVEKIT_ROOM_MAX_PARTICIPANTS", "4"))


def is_configured() -> bool:
    return bool(
        api is not None
        and LIVEKIT_API_URL
        and LIVEKIT_API_KEY
        and LIVEKIT_API_SECRET
    )


def _require_configuration() -> None:
    if api is None:
        raise RuntimeError(
            "LiveKit bagimliliklari eksik. Demo modunda backend acilabilir, ancak "
            "LiveKit ozellikleri icin eksik paketleri kurun "
            f"(orijinal hata: {LIVEKIT_IMPORT_ERROR})."
        )

    if not is_configured():
        raise RuntimeError(
            "LiveKit yapilandirmasi eksik. LIVEKIT_API_URL, LIVEKIT_API_KEY ve "
            "LIVEKIT_API_SECRET degiskenlerini tanimlayin."
        )


def _proto_to_dict(message: Any) -> Dict[str, Any]:
    if MessageToDict is None:
        raise RuntimeError(
            "google.protobuf kullanilamiyor. LiveKit/protobuf bagimliliklarini kurun."
        )
    return MessageToDict(message, preserving_proto_field_name=True)


def _normalize_ws_url(url: str) -> str:
    if url.startswith("ws://") or url.startswith("wss://"):
        return url
    if url.startswith("https://"):
        return "wss://" + url[len("https://") :]
    if url.startswith("http://"):
        return "ws://" + url[len("http://") :]
    return url


def public_ws_url() -> str:
    candidate = LIVEKIT_WS_URL or LIVEKIT_API_URL
    return _normalize_ws_url(candidate)


def _metadata_json(payload: Optional[Dict[str, Any]]) -> str:
    return json.dumps(payload or {}, ensure_ascii=False)


def create_access_token(
    room_name: str,
    participant_id: str,
    display_name: str,
    metadata: Optional[Dict[str, Any]] = None,
    *,
    room_admin: bool = False,
    can_publish: bool = True,
    can_subscribe: bool = True,
) -> str:
    _require_configuration()

    grants = api.VideoGrants(
        room_join=True,
        room=room_name,
        room_admin=room_admin,
        can_publish=can_publish,
        can_subscribe=can_subscribe,
        can_publish_data=True,
    )

    return (
        api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        .with_identity(participant_id)
        .with_name(display_name)
        .with_metadata(_metadata_json(metadata))
        .with_grants(grants)
        .to_jwt()
    )


def build_webhook_receiver() -> Any:
    _require_configuration()
    verifier = api.TokenVerifier(
        api_key=LIVEKIT_API_KEY,
        api_secret=LIVEKIT_API_SECRET,
    )
    return api.WebhookReceiver(verifier)


async def create_room(
    room_name: str,
    metadata: Optional[Dict[str, Any]] = None,
    *,
    empty_timeout: Optional[int] = None,
    departure_timeout: Optional[int] = None,
    max_participants: Optional[int] = None,
) -> Dict[str, Any]:
    _require_configuration()

    request = api.CreateRoomRequest()
    request.name = room_name
    request.empty_timeout = empty_timeout or LIVEKIT_ROOM_EMPTY_TIMEOUT
    request.departure_timeout = departure_timeout or LIVEKIT_ROOM_DEPARTURE_TIMEOUT
    request.max_participants = max_participants or LIVEKIT_ROOM_MAX_PARTICIPANTS
    request.metadata = _metadata_json(metadata)

    async with api.LiveKitAPI(
        url=LIVEKIT_API_URL,
        api_key=LIVEKIT_API_KEY,
        api_secret=LIVEKIT_API_SECRET,
    ) as client:
        try:
            room = await client.room.create_room(request)
            return _proto_to_dict(room)
        except api.TwirpError as exc:
            if exc.status == 409:
                return {"name": room_name, "status": "exists"}
            raise


async def list_rooms(names: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    _require_configuration()

    request = api.ListRoomsRequest()
    if names:
        request.names.extend(list(names))

    async with api.LiveKitAPI(
        url=LIVEKIT_API_URL,
        api_key=LIVEKIT_API_KEY,
        api_secret=LIVEKIT_API_SECRET,
    ) as client:
        response = await client.room.list_rooms(request)
        return _proto_to_dict(response)


async def delete_room(room_name: str) -> Dict[str, Any]:
    _require_configuration()

    request = api.DeleteRoomRequest()
    request.room = room_name

    async with api.LiveKitAPI(
        url=LIVEKIT_API_URL,
        api_key=LIVEKIT_API_KEY,
        api_secret=LIVEKIT_API_SECRET,
    ) as client:
        response = await client.room.delete_room(request)
        return _proto_to_dict(response)


async def list_participants(room_name: str) -> Dict[str, Any]:
    _require_configuration()

    request = api.ListParticipantsRequest()
    request.room = room_name

    async with api.LiveKitAPI(
        url=LIVEKIT_API_URL,
        api_key=LIVEKIT_API_KEY,
        api_secret=LIVEKIT_API_SECRET,
    ) as client:
        response = await client.room.list_participants(request)
        return _proto_to_dict(response)


async def remove_participant(room_name: str, identity: str) -> Dict[str, Any]:
    _require_configuration()

    request = api.RoomParticipantIdentity()
    request.room = room_name
    request.identity = identity

    async with api.LiveKitAPI(
        url=LIVEKIT_API_URL,
        api_key=LIVEKIT_API_KEY,
        api_secret=LIVEKIT_API_SECRET,
    ) as client:
        response = await client.room.remove_participant(request)
        return _proto_to_dict(response)


async def start_track_egress(
    room_name: str,
    track_id: str,
    filepath: str,
) -> Dict[str, Any]:
    _require_configuration()

    request = api.TrackEgressRequest()
    request.room_name = room_name
    request.track_id = track_id
    request.file.filepath = filepath

    async with api.LiveKitAPI(
        url=LIVEKIT_API_URL,
        api_key=LIVEKIT_API_KEY,
        api_secret=LIVEKIT_API_SECRET,
    ) as client:
        response = await client.egress.start_track_egress(request)
        return _proto_to_dict(response)


async def stop_egress(egress_id: str) -> Dict[str, Any]:
    _require_configuration()

    request = api.StopEgressRequest()
    request.egress_id = egress_id

    async with api.LiveKitAPI(
        url=LIVEKIT_API_URL,
        api_key=LIVEKIT_API_KEY,
        api_secret=LIVEKIT_API_SECRET,
    ) as client:
        response = await client.egress.stop_egress(request)
        return _proto_to_dict(response)
