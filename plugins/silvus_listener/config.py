from dataclasses import dataclass
@dataclass
class SilvusConfig:
    zero_axis: str='forward'
    positive: str='cw'
    default_bearing_error_deg: float=5.0
    default_confidence: int=75
    replay_path: str|None=None
    status_buffer_max: int=100
