from enum import Enum

class Platform(str, Enum):
    LAZADA = "lazada"

class ProductMetadata(str, Enum):
    PLATFORM = "platform"
    SOURCE_ID = "sourceId"
