from sqlalchemy import Column, String, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Enum as SAEnum
from db.base import Base
import enum


class DeviceType(enum.Enum):
    camera = "camera"
    nvr = "nvr"


class StreamingDevice(Base):
    __tablename__ = "streaming_devices"

    device_id = Column(String, primary_key=True, index=True)
    device_type = Column(SAEnum(DeviceType, name="device_type_enum", native_enum=False), nullable=False)
    ip = Column(String, nullable=True)
    port = Column(Integer, nullable=True)
    username = Column(String, nullable=True)
    password = Column(String, nullable=True)
    meta_data = Column(JSONB, nullable=True)
