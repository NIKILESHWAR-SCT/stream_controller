import asyncio
import base64
import cv2
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _grab_frame_blocking(rtsp_url: str, timeout_seconds: int = 10):
    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        cap.release()
        raise RuntimeError("Unable to open RTSP stream")

    # try to read several frames to allow stream warmup
    for _ in range(5):
        ret, frame = cap.read()
        if ret and frame is not None:
            break
    else:
        cap.release()
        raise RuntimeError("Failed to read frame from RTSP stream")

    # encode as JPEG
    ret2, buf = cv2.imencode('.jpg', frame)
    cap.release()
    if not ret2:
        raise RuntimeError("Failed to encode frame")
    return buf.tobytes()


async def grab_frame_base64(rtsp_url: str) -> str:
    loop = asyncio.get_running_loop()
    try:
        jpeg_bytes = await loop.run_in_executor(None, _grab_frame_blocking, rtsp_url)
    except Exception as e:
        logger.exception("Error grabbing frame from %s: %s", rtsp_url, e)
        raise

    b64 = base64.b64encode(jpeg_bytes).decode('utf-8')
    return b64
