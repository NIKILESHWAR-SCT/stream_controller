from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.streaming import (
    FrameRequest,
    CameraFrameResponse,
    NVRFrameResponse,
    CapabilitiesRequest,
    CameraDiscoveryResponse,
    NVRDiscoveryResponse,
)
from db.session import get_db
from models.streaming_device import StreamingDevice, DeviceType
from services.streaming_service import grab_frame_base64, _grab_frame_blocking
from fastapi.responses import StreamingResponse
from services.capabilities_service import fetch_capabilities_from_onboarding, extract_discovery_response
import httpx
from sqlalchemy import select
import logging
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/stream")


@router.post("/frame")
async def get_frame(payload: FrameRequest, db: AsyncSession = Depends(get_db)):
    # fetch device
    stmt = select(StreamingDevice).where(StreamingDevice.device_id == payload.device_id)
    res = await db.execute(stmt)
    device = res.scalars().first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    if payload.device_type not in ("camera", "nvr"):
        raise HTTPException(status_code=400, detail="device_type must be 'camera' or 'nvr'")

    if device.device_type.value != payload.device_type:
        raise HTTPException(status_code=400, detail="device_type mismatch with stored device")

    # Camera handling
    if payload.device_type == "camera":
        meta = device.meta_data or {}
        rtsp = meta.get("rtsp_url")
        if not rtsp:
            raise HTTPException(status_code=400, detail="RTSP url not found in meta_data")

        try:
            b64 = await grab_frame_base64(rtsp)
        except Exception as e:
            logger.exception("Failed to grab frame for device %s", device.device_id)
            raise HTTPException(status_code=502, detail="Failed to fetch frame from RTSP")

        # Return JSON response with base64-encoded frame
        return {
            "device_id": device.device_id,
            "frame": b64
        }

    # NVR handling
    if payload.device_type == "nvr":
        if not payload.camera_id:
            raise HTTPException(status_code=400, detail="camera_id is required for nvr devices")

        meta = device.meta_data or {}
        
        # Support both formats: "cameras" (list of dicts) and "camera_ids" (list of tokens)
        cameras = None
        camera_ids = None
        rtsp = None
        
        if isinstance(meta, dict):
            cameras = meta.get("cameras")
            camera_ids = meta.get("camera_ids")
        
        # Try to match in cameras list format (dicts with rtsp_url)
        if cameras and isinstance(cameras, list):
            for cam in cameras:
                if isinstance(cam, dict) and cam.get("camera_id") == payload.camera_id:
                    rtsp = cam.get("rtsp_url")
                    break
        
        # If not found, try camera_ids format (token strings)
        if not rtsp and camera_ids and isinstance(camera_ids, list):
            if payload.camera_id not in camera_ids:
                raise HTTPException(status_code=404, detail="camera_id not found in device camera_ids")
            
            # For NVR token-based cameras, build RTSP URL from device IP, port, and token
            username = device.username or "admin"
            password = device.password or "admin"
            device_ip = device.ip
            device_port = device.port or 554
            
            # Extract channel number from token (e.g., VideoSourceToken001 -> 01)
            try:
                token_parts = payload.camera_id.split("Token")
                if len(token_parts) > 1:
                    channel_num = token_parts[-1]
                    channel = channel_num.zfill(2)
                else:
                    channel = "01"
            except Exception:
                channel = "01"
            
            rtsp = f"rtsp://{username}:{password}@{device_ip}:{device_port}/Streaming/Unicast/channels/{channel}01"
        
        if not rtsp:
            raise HTTPException(status_code=404, detail="RTSP url not found for camera_id")

        try:
            loop = asyncio.get_running_loop()
            b64 = await loop.run_in_executor(None, _grab_frame_blocking, rtsp)
        except Exception:
            logger.exception("Failed to grab frame for NVR device %s camera %s", device.device_id, payload.camera_id)
            raise HTTPException(status_code=502, detail="Failed to fetch frame from RTSP")

        # Return JSON response with base64-encoded frame
        return {
            "device_id": device.device_id,
            "camera_id": payload.camera_id,
            "frame": b64
        }


@router.post("/capabilities")
async def capabilities_proxy(payload: CapabilitiesRequest, db: AsyncSession = Depends(get_db)):
    # fetch device to get credentials
    stmt = select(StreamingDevice).where(StreamingDevice.device_id == payload.device_id)
    res = await db.execute(stmt)
    device = res.scalars().first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    username = device.username
    password = device.password
    if username is None or password is None:
        raise HTTPException(status_code=400, detail="Device credentials not available")

    try:
        onboarding_resp = await fetch_capabilities_from_onboarding(payload.ip, payload.port, username, password)
    except httpx.RequestError:
        logger.exception("Request to device_onboarding failed for device %s", payload.device_id)
        raise HTTPException(status_code=502, detail="Failed to contact device_onboarding service")
    except Exception:
        logger.exception("Error while calling device_onboarding for device %s", payload.device_id)
        raise HTTPException(status_code=502, detail="Failed to contact device_onboarding service")

    # prepare refined response
    refined = extract_discovery_response(payload.device_id, device.device_type.value, onboarding_resp)
    return refined
