from .base import BaseRepository
from bson import ObjectId

class RawDataRepository(BaseRepository):
    def __init__(self):
        super().__init__("raw_data")