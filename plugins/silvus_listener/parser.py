import re,datetime
HDR=re.compile(r"\[(\d+\.\d+\.\d+\.\d+)\].*Heading \(deg\):\s*([-\d\.]+)")
DAT=re.compile(r"\[(\d+\.\d+\.\d+\.\d+):(\d+)\]\s*([-\d\.]+)\s*,\s*([-\d\.]+)\s*,\s*([-\d\.]+)\s*,\s*\[([-\d\.]+)\s*,\s*([-\d\.]+)\]")

def us_to_iso(u:int):
    return datetime.datetime.utcfromtimestamp(u/1_000_000).replace(tzinfo=datetime.timezone.utc).isoformat()

def parse_lines(lines):
    hdg=None
    for ln in lines:
        m=HDR.search(ln)
        if m:
            hdg=float(m.group(2)); continue
        m=DAT.search(ln)
        if m:
            yield {'time_utc':us_to_iso(int(m.group(2))), 'freq_mhz':float(m.group(4)), 'aoa1_deg':float(m.group(6)), 'aoa2_deg':float(m.group(7)), 'heading_deg':hdg}
