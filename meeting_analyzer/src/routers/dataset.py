from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter()

@router.post("/build/{session_id}")
async def build_dataset(session_id: str):
    pass

@router.get("/{session_id}")
async def get_dataset_status(session_id: str):
    pass
