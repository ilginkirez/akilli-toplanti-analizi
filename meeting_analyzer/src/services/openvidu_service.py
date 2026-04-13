import base64
import json
import os
from typing import Any, Dict, Optional

import httpx

OV_URL = os.getenv("OPENVIDU_URL", "http://localhost:4443").rstrip("/")
OV_SECRET = os.getenv("OPENVIDU_SECRET", "MY_SECRET")
OV_VERIFY_SSL = os.getenv("SSL_VERIFY", "false").lower() == "true"


def _headers() -> Dict[str, str]:
    credentials = base64.b64encode(f"OPENVIDUAPP:{OV_SECRET}".encode()).decode()
    return {
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/json",
    }


async def _request(method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    async with httpx.AsyncClient(verify=OV_VERIFY_SSL, timeout=30.0) as client:
        response = await client.request(
            method,
            f"{OV_URL}{path}",
            headers=_headers(),
            json=payload,
        )
        if response.status_code == 204:
            return {}
        if response.status_code == 409:
            try:
                return response.json()
            except Exception:
                return {"status": "conflict"}
        response.raise_for_status()
        return response.json()


async def create_session(session_id: str) -> Dict[str, Any]:
    payload = {
        "customSessionId": session_id,
        "recordingMode": "MANUAL",
        "defaultRecordingProperties": {
            "outputMode": "INDIVIDUAL",
            "hasAudio": True,
            "hasVideo": False,
            "name": session_id,
        },
    }
    result = await _request("POST", "/openvidu/api/sessions", payload)
    if result.get("status") == "conflict":
        return {"id": session_id, "sessionId": session_id, "status": "conflict"}
    return result


async def create_connection(
    session_id: str,
    participant_id: str,
    display_name: str,
    device_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    server_data = json.dumps(
        {
            "participant_id": participant_id,
            "display_name": display_name,
            "session_id": session_id,
            "device_info": device_info or {},
        }
    )
    payload = {
        "type": "WEBRTC",
        "role": "PUBLISHER",
        "record": True,
        "data": server_data,
    }
    connection = await _request(
        "POST",
        f"/openvidu/api/sessions/{session_id}/connection",
        payload,
    )
    return connection


async def create_token(
    session_id: str,
    participant_id: str,
) -> Dict[str, Any]:
    """Backward-compatible helper kept for older router/test call sites."""
    return await create_connection(
        session_id=session_id,
        participant_id=participant_id,
        display_name=participant_id,
    )


async def start_individual_recording(session_id: str, name: Optional[str] = None) -> Dict[str, Any]:
    payload = {
        "session": session_id,
        "name": name or session_id,
        "outputMode": "INDIVIDUAL",
        "hasAudio": True,
        "hasVideo": False,
    }
    return await _request("POST", "/openvidu/api/recordings/start", payload)


async def stop_recording(recording_id: str) -> Dict[str, Any]:
    return await _request("POST", f"/openvidu/api/recordings/stop/{recording_id}")


async def get_recording(recording_id: str) -> Dict[str, Any]:
    return await _request("GET", f"/openvidu/api/recordings/{recording_id}")


async def close_session(session_id: str) -> None:
    await _request("DELETE", f"/openvidu/api/sessions/{session_id}")
