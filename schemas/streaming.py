from pydantic import BaseModel, Field
from typing import Optional, List, Any, Literal


class FrameRequest(BaseModel):
    device_id: str
    device_type: str
    camera_id: Optional[str] = None


class CameraFrameResponse(BaseModel):
    device_id: str
    frame: str


class NVRFrameResponse(BaseModel):
    device_id: str
    camera_id: str
    frame: str


class CapabilitiesRequest(BaseModel):
    device_id: str
    ip: str
    port: int


class CameraDiscoveryResponse(BaseModel):
    device_id: str
    device_type: Literal["camera"] = "camera"


class NVRDiscoveryResponse(BaseModel):
    device_id: str
    device_type: Literal["nvr"] = "nvr"
    camera_count: int
    camera_id_sources: List[str]
