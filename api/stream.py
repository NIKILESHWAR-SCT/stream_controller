from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import StreamingResponse
from sqlalchemy import select
import asyncio
import logging
import httpx

from schemas.streaming import (
    FrameRequest,
    CapabilitiesRequest,
)
from db.session import get_db
from models.streaming_device import StreamingDevice
from services.streaming_service import _grab_frame_blocking
from services.capabilities_service import (
    fetch_capabilities_from_onboarding,
    extract_discovery_response,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/stream")


# -------------------------------------------------------------------
# FRAME ENDPOINT
# -------------------------------------------------------------------
@router.post("/frame")
async def get_frame(payload: FrameRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(StreamingDevice).where(
        StreamingDevice.device_id == payload.device_id
    )
    res = await db.execute(stmt)
    device = res.scalars().first()

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    if payload.device_type not in ("camera", "nvr"):
        raise HTTPException(
            status_code=400,
            detail="device_type must be 'camera' or 'nvr'"
        )

    if device.device_type.value != payload.device_type:
        raise HTTPException(
            status_code=400,
            detail="device_type mismatch with stored device"
        )

    meta = device.meta_data

    # ---------------------------------------------------------------
    # CAMERA DEVICE
    # ---------------------------------------------------------------
    if payload.device_type == "camera":
        if not isinstance(meta, dict):
            raise HTTPException(
                status_code=400,
                detail="Invalid meta_data format for camera"
            )

        rtsp = meta.get("rtsp_url")
        if not rtsp:
            raise HTTPException(
                status_code=400,
                detail="RTSP url not found in meta_data"
            )

        try:
            loop = asyncio.get_running_loop()
            jpeg_bytes = await loop.run_in_executor(
                None, _grab_frame_blocking, rtsp
            )
        except Exception:
            logger.exception(
                "Failed to grab frame for camera %s",
                device.device_id
            )
            raise HTTPException(
                status_code=502,
                detail="Failed to fetch frame from RTSP"
            )

        return StreamingResponse(
            iter([jpeg_bytes]),
            media_type="image/jpeg"
        )

    # ---------------------------------------------------------------
    # NVR DEVICE
    # ---------------------------------------------------------------
    if payload.device_type == "nvr":
        if not payload.camera_id:
            raise HTTPException(
                status_code=400,
                detail="camera_id is required for nvr devices"
            )

        if not isinstance(meta, list):
            raise HTTPException(
                status_code=400,
                detail="Invalid meta_data format for nvr"
            )

        rtsp = None
        for cam in meta:
            if (
                isinstance(cam, dict)
                and cam.get("camera_id") == payload.camera_id
            ):
                rtsp = cam.get("rtsp_url")
                break

        if not rtsp:
            raise HTTPException(
                status_code=404,
                detail="RTSP url not found for camera_id in meta_data"
            )

        try:
            loop = asyncio.get_running_loop()
            jpeg_bytes = await loop.run_in_executor(
                None, _grab_frame_blocking, rtsp
            )
        except Exception:
            logger.exception(
                "Failed to grab frame for NVR %s camera %s",
                device.device_id,
                payload.camera_id
            )
            raise HTTPException(
                status_code=502,
                detail="Failed to fetch frame from RTSP"
            )

        return StreamingResponse(
            iter([jpeg_bytes]),
            media_type="image/jpeg"
        )


# -------------------------------------------------------------------
# CAPABILITIES ENDPOINT (PROXY)
# -------------------------------------------------------------------
@router.post("/capabilities")
async def capabilities_proxy(
    payload: CapabilitiesRequest,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(StreamingDevice).where(
        StreamingDevice.device_id == payload.device_id
    )
    res = await db.execute(stmt)
    device = res.scalars().first()

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    if not device.username or not device.password:
        raise HTTPException(
            status_code=400,
            detail="Device credentials not available"
        )

    try:
        onboarding_resp = await fetch_capabilities_from_onboarding(
            payload.ip,
            payload.port,
            device.username,
            device.password,
        )
    except httpx.RequestError:
        logger.exception(
            "device_onboarding request failed for %s",
            payload.device_id
        )
        raise HTTPException(
            status_code=502,
            detail="Failed to contact device_onboarding service"
        )
    except Exception:
        logger.exception(
            "Unexpected error calling device_onboarding for %s",
            payload.device_id
        )
        raise HTTPException(
            status_code=502,
            detail="Failed to contact device_onboarding service"
        )

    return extract_discovery_response(
        payload.device_id,
        device.device_type.value,
        onboarding_resp,
    )
