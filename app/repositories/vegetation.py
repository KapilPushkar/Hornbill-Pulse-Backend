from .base import BaseRepository
from bson import ObjectId

class VegetationRepository(BaseRepository):
    def __init__(self):
        super().__init__("vegetation_stats")

    async def update_report_path(self, stats_id: str, report_path: str) -> bool:
        result = await self.update(
            stats_id,
            {"report_path": report_path}
        )
        return result