print("------------------------------------------------------")
# Find directory for where to put the egm96_15.gtx file
print(
    "For EGM96 transformations, copy "
    "egm96_15.gtx"
    " from the downloaded location to this folder:"
)
from pyproj import datadir

print(datadir.get_data_dir())
print("------------------------------------------------------")
