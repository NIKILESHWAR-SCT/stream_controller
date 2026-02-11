import httpx
import logging
from typing import Dict, Any, List
from core.config import settings

logger = logging.getLogger(__name__)


async def fetch_capabilities_from_onboarding(ip: str, port: int, username: str, password: str) -> Dict[str, Any]:
    url = settings.SERVICE_DEVICE_ONBOARDING_URL
    payload = {
        "camera_type": "onvif",
        "host": ip,
        "port": 80,
        "username": username,
        "password": password,
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            resp = await client.post(url, json=payload)
        except httpx.RequestError as e:
            logger.exception("Request to device_onboarding failed: %s", e)
            raise

    if resp.status_code != 200:
        logger.error("device_onboarding returned non-200: %s - %s", resp.status_code, resp.text)
        resp.raise_for_status()

    data = resp.json()
    return data


def extract_discovery_response(device_id: str, device_type: str, onboarding_response: Dict[str, Any]):
    # Attempt to find VideoSource tokens in a flexible way
    tokens: List[str] = []
    # common path: data -> video_sources -> sources
    try:
        sources = onboarding_response.get('data', {}).get('video_sources', {}).get('sources', [])
        for s in sources:
            token = s.get('token') or s.get('VideoSourceToken')
            if token:
                tokens.append(token)
    except Exception:
        logger.exception("Failed to extract tokens from onboarding response")

    if device_type == 'camera':
        return {"device_id": device_id, "device_type": "camera"}

    # nvr
    return {
        "device_id": device_id,
        "device_type": "nvr",
        "camera_count": len(tokens),
        "camera_id_sources": tokens,
    }
