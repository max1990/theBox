"""
Constants for Dspnor plugin - Dronnur-2D Naval LPI/LPD radar
"""

# Discovery and info ports
DEFAULT_DISCOVERY_MULTICAST = "227.228.229.230"
DEFAULT_DISCOVERY_PORT = 59368
DEFAULT_INFO_TCP_PORT = 59623
DEFAULT_RESET_MULTICAST_PORT = 59369

# Service ports
DEFAULT_CAT010_PORT = 4010
DEFAULT_NMEA_UDP_PORT = 60000

# D2D Protocol constants
D2D_PROTOCOL = "D2D"
D2D_VERSION = "1.0"
D2D_TYPE_TEXT = "TEXT"
D2D_TYPE_BINARY = "BINARY"

# CAT-010 Item IDs (per ICD)
CAT010_ITEM_140 = 0x8C  # Time of Day
CAT010_ITEM_161 = 0xA1  # Track Number
CAT010_ITEM_040 = 0x28  # Target Report Descriptor
CAT010_ITEM_041 = 0x29  # Target Address
CAT010_ITEM_042 = 0x2A  # Track Quality
CAT010_ITEM_200 = 0xC8  # Ground Speed
CAT010_ITEM_202 = 0xCA  # Track Angle Rate
CAT010_ITEM_220 = 0xDC  # Mode 3/A Code
CAT010_ITEM_245 = 0xF5  # Target Identification

# MMSI bit position in I010/245
MMSI_BIT_POSITION = 54

# NMEA sentence types
NMEA_RMC = "RMC"  # Recommended Minimum
NMEA_VTG = "VTG"  # Track Made Good and Ground Speed
NMEA_GGA = "GGA"  # Global Positioning System Fix Data
NMEA_HDG = "HDG"  # Heading - Deviation & Variation

# Units conversion
MPS_TO_KTS = 1.94384
KTS_TO_MPS = 0.514444
M_TO_KM = 0.001
KM_TO_M = 1000.0

# Default confidence mapping
DEFAULT_CONF_MAP = "snr_db:linear:0:30"

# Reconnect backoff (milliseconds)
DEFAULT_RECONNECT_BACKOFF = [500, 1000, 2000, 5000]

# Message rate limiting
DEFAULT_MAX_MSG_RATE_HZ = 200
DEFAULT_HEARTBEAT_EXPECTED_SEC = 5

# Buffer sizes
DEFAULT_BUFFER_BYTES = 65536
DEFAULT_CONNECT_TIMEOUT_SEC = 5

# Discovery beacon size
DISCOVERY_BEACON_SIZE = 40
