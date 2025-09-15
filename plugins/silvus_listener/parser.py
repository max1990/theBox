import re
import datetime
from typing import Iterable, Dict, Generator

# Header line example:
# [172.16.0.46]  Lat/Lon : (36.6009,-121.8947), Heading (deg): 101.2
HDR = re.compile(
    r"\[(?P<ip>\d+\.\d+\.\d+\.\d+)\]\s+Lat/Lon\s*:\s*\((?P<lat>[-\d\.]+)\s*,\s*(?P<lon>[-\d\.]+)\)\s*,\s*Heading\s*\(deg\)\s*:\s*(?P<hdg>[-\d\.]+)"
)

# Data line example:
# [172.16.0.46:1749599078856027] -74.69, 2462.00, 20.00, [133.109, 304.816], [130, 302]
DAT = re.compile(
    r"\[(?P<ip>\d+\.\d+\.\d+\.\d+):(?P<ts>\d+)\]\s*(?P<power>[-\d\.]+)\s*,\s*(?P<fc>[-\d\.]+)\s*,\s*(?P<bw>[-\d\.]+)\s*,\s*\[(?P<aoa1>[-\d\.]+)\s*,\s*(?P<aoa2>[-\d\.]+)\]"
)

def us_to_iso(ts_us: int) -> str:
    # Silvus timestamps are microseconds since epoch (UTC)
    return datetime.datetime.utcfromtimestamp(ts_us / 1_000_000).replace(tzinfo=datetime.timezone.utc).isoformat()

def parse_lines(lines: Iterable[str]) -> Generator[Dict, None, None]:
    """
    Yields dicts with the minimum we need: time_utc, freq_mhz, aoa1_deg, aoa2_deg, heading_deg
    """
    last_hdg = None
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        m = HDR.search(line)
        if m:
            last_hdg = float(m.group("hdg"))
            continue
        m = DAT.search(line)
        if m:
            ts_us = int(m.group("ts"))
            yield {
                "time_utc": us_to_iso(ts_us),
                "freq_mhz": float(m.group("fc")),
                "aoa1_deg": float(m.group("aoa1")),
                "aoa2_deg": float(m.group("aoa2")),
                "heading_deg": last_hdg,   # may be None if GPS/heading not present
            }
