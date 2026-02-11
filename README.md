# streaming_controller

FastAPI microservice to provide live frames from streaming devices and proxy device capability calls to `device_onboarding`.

Run: `python -m streaming_controller.main` (or `uvicorn streaming_controller.app:app --host 0.0.0.0 --port 8002`)

Requirements
- Python 3.11
- Postgres DB
- See `requirements.txt` for pip dependencies.

DB configuration
Environment variables (defaults shown):

- `DB_NAME=streaming_controller`
- `DB_HOST=192.168.1.144`
- `DB_PORT=5432`
- `DB_USER=postgres`
- `DB_PASSWORD=vigilxdev`

Database schema
- Table: `streaming_devices`
  - `device_id` VARCHAR PRIMARY KEY
  - `device_type` ENUM('camera','nvr')
  - `ip` VARCHAR
  - `port` INTEGER
  - `username` VARCHAR
  - `password` VARCHAR
  - `meta_data` JSONB

meta_data formats

Camera: `{ "rtsp_url": "rtsp://..." }`

NVR: `{ "cameras": [ { "camera_id": "cam_1", "rtsp_url": "rtsp://..." } ] }`

APIs

1) POST `/api/v1/stream/frame`
- Request body:
  - `device_id` (string)
  - `device_type` (`camera` or `nvr`)
  - `camera_id` (required when `device_type` is `nvr`)
- Behavior:
  - Fetch device from DB; read RTSP URL from `meta_data` (camera) or `meta_data.cameras` for NVR
  - Grab a single frame with OpenCV
  - Return base64-encoded JPEG
- Responses:
  - Camera: `{ "device_id": "...", "frame": "base64..." }`
  - NVR: `{ "device_id": "...", "camera_id": "...", "frame": "base64..." }`

2) POST `/api/v1/stream/capabilities`
- Request body:
  - `device_id` (string)
  - `ip` (string)
  - `port` (number)
- Behavior:
  - Fetch credentials from DB
  - Forward request to `device_onboarding` at `http://localhost:8001/api/v1/cameras/capabilities`
  - Parse response for `data.video_sources.sources[].token` and return refined discovery result

Error Handling
- Returns 4xx for invalid input or device not found
- Returns 502 when RTSP fetch or downstream service fails

Notes
- No authentication is implemented
- Uses async SQLAlchemy + `asyncpg` driver
- OpenCV operations run in threadpool to avoid blocking the event loop
