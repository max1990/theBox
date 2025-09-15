from mvp.db_adapter import DBAdapter


class RangeStub:
    def __init__(self, db: DBAdapter, range_km: float):
        self.db = db
        self.range_km = range_km

    def apply_on_first(self, track_id: str):
        self.db.update_track_range(track_id, self.range_km)


