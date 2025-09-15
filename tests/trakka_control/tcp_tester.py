import socket
import json
from sys import *
import binascii
import time
import struct
import math
from pyproj import Proj, transform
from pyproj import Transformer
import array

import tcp_sender
import trakka_rx_statemachine

import argparse, math, time, sys, os
# Ensure project root is on sys.path so `plugins` is importable when run from tests/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from plugins.trakka_control.tcp_sender import tcp_sender

##########################################################################
#
#  This is a python 3 class for testing portions of the tcp_sender object imported above
#  As of 2025-09-05 it has only been tested with the simulator.
#
#  The pyproj included with install did not contain the egm96_15.gtx file needed to do the 
#  transformations in altitude from the WGS84 HAE values.  
#  If you recieve values with no change from HAE in all cases use the included egm96* files to set that up.
#  
#  2025-09-05 PB
#
##########################################################################

#WGS84 HAE value for testing with Geopoint
lla_x = -118.1231
lla_y = 34.1231
lla_z = 95



print ('-- Sending to Simulator--------------------------')
s = tcp_sender.tcp_sender()

# print ('----------------------------- Enable and recieve Drone Identification Messages ')

###  ENABLE        ---- always send this to enable the data return ----
s.modify_mti(4,30)


# ### Recieve           # this listens to messages we need to implenemt this gracefully because it tells us what it sees
# sm = trakka_rx_statemachine.trakka_rx_statemachine()
# while True:
#     try:
#         s.get_azimuth_status()
#         rdata = s.tcpSock.recv(4096) 
#         # self.tcpSock.close()
#         sm.process_data(rdata)
#     except socket.timeout:
#         pass
# print ('----------------------------- Enable and recieve Drone Identification Messages ')


print ('----------------------------- Proportional Control ')

# starting at 0,0
s.set_gimbal_mode(0)                   # set to rate mode
print ('---------------------------------')
s.proportional_control(16,67)        # how to call the abiity to slew -- this one will block until the camera reaches it

print ('----------------------------- Proportional Control ')



# print ('----------------------------- GeoPoint ')

# egm_x, egm_y, egm_z = s.wgs84_to_egm96(lla_x,lla_y,lla_z)
# ecef_x, ecef_y, ecef_z = s.lla_to_ecef(egm_x, egm_y, egm_z)

# print('LLA Longitude: {}, LLA Latitude: {}, LLA Height : {}'.format(lla_x, lla_y, lla_z))
# print('EGM96 Longitude: {}, EGM96 Latitude: {}, EGM96 Height : {}'.format(egm_x, egm_y, egm_z))
# print('ECEF Longitude: {}, ECEF Latitude: {}, ECEF Height : {}'.format(ecef_x, ecef_y, ecef_z))

# print ('Setting ECEF')
# s.setpoint_ecef(ecef_x, ecef_y, ecef_z)
# s.set_gimbal_mode(3)                  # sets the camera to geo-point

# print ('Done ECEF')

# print ('----------------------------- GeoPoint ')



# print ('----------------------------- SET GIMBAL MODE')

# g_mode = s.get_gimbal_mode()
# print ('Reading Gimbal Mode ================================ : ',g_mode)
# s.set_gimbal_mode(1)
# time.sleep(3)
# g_mode = s.get_gimbal_mode()
# print ('Reading Gimbal Mode ================================ : ',g_mode)
# s.set_gimbal_mode(2)
# time.sleep(3)
# g_mode = s.get_gimbal_mode()
# print ('Reading Gimbal Mode ================================ : ',g_mode)
# s.set_gimbal_mode(3)
# time.sleep(3)
# g_mode = s.get_gimbal_mode()
# print ('Reading Gimbal Mode ================================ : ',g_mode)
# s.set_gimbal_mode(0)
# time.sleep(3)
# g_mode = s.get_gimbal_mode()
# print ('Reading Gimbal Mode ================================ : ',g_mode)

# print ('----------------------------- SET GIMBAL MODE')


# print ('----------------------------- SET ZOOM')
# active_sensor = 1
# zl_status = s.get_zoom_status(active_sensor)
# print ('Read Zoom Status Sensor {}: {} '.format(active_sensor,zl_status))
# s.set_zoom_rate(active_sensor,'RATE',-0.1)
# time.sleep(2)
# zl_status = s.get_zoom_status(active_sensor)
# print ('Read Zoom Status Sensor {}: {} '.format(active_sensor,zl_status))

# s.set_zoom_rate(active_sensor,'RATE',0.0)
# zl_status = s.get_zoom_status(active_sensor)
# print ('Read Zoom Status Sensor {}: {} '.format(active_sensor,zl_status))
# zl_status = s.get_zoom_status(active_sensor)
# print ('Read Zoom Status Sensor {}: {} '.format(active_sensor,zl_status))
# print ('----------------------------- SET ZOOM')



# print ('----------------------------- SET ELEVATION')
# el_status = s.get_elevation_status()
# print ('Elevation Status: ',el_status)
# print ('Degree equivalent: ',math.degrees(el_status))
# print ('Changing Elevation')
# s.set_elevation_rate(-0.25)
# time.sleep(3.4)
# s.set_elevation_rate(0.0)
# print ('Stopping Elevation')
# el_status = s.get_elevation_status()
# print ('Elevation Status: ',el_status)
# print ('Degree equivalent: ',math.degrees(el_status))
# el_status = s.get_elevation_status()
# print ('Elevation Status: ',el_status)
# print ('Degree equivalent: ',math.degrees(el_status))
# print ('----------------------------- SET ELEVATION')



# print ('----------------------------- SET AZIMUTH')
# az_status = s.get_azimuth_status()
# print ('Azimuth Status: ',az_status)
# print ('Degree equivalent: ',math.degrees(az_status))
# s.set_azimuth_rate(0.1)
# time.sleep(2.7)
# s.set_azimuth_rate(0.0)
# az_status = s.get_azimuth_status()
# print ('AZ-Status : ',az_status)
# print ('Degree equivalent: ',math.degrees(az_status))
# time.sleep(2)
# az_status = s.get_azimuth_status()
# print ('AZ-Status : ',az_status)
# print ('Degree equivalent: ',math.degrees(az_status))
# print ('----------------------------- SET AZIMUTH')

print ('==========================================')

print ('EXITING...')
exit()








