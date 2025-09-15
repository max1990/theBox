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

import trakka_rx_statemachine
##########################################################################
#
#  This is a python 3 class for sending tcp packets to the Trakka camera.
#  As of 2025-09-05 it has only been tested with the simulator.
#  
#  2025-09-05 PB
#
##########################################################################


class tcp_sender:
 
    #tcp_host = "127.0.0.1"
    tcp_host = "169.254.1.181"
    tcp_port = 51555
    tcp_buf  = 1024

    tcpSock = socket.socket()
    tcpSock.settimeout(1)
    tcpSock.connect((tcp_host,tcp_port))

    sync1 = 167
    sync2 = 84
    
    gain = 2.5                                              # how fast the camera moves (deg/sec * gain * error%)
    rate_threshold = 30                                     # max rate (60 is max)

    exit_threshold_deg  = .1                                # how close before we say stop (0.1 degree)
    exit_threshold_rad = math.radians(exit_threshold_deg)   # same as above
    
    current_az = 0
    current_el = 0

    def calc_checksum_ba(self,data):
        #data is passed in as the full packet minus the checksum bytes
        sum1 = 0
        sum2 = 0
        
        for i in range(2, len(data)):
            byte_val = data[i]
            sum1 = (sum1 + byte_val) % 255
            sum2 = (sum2 + sum1) % 255

        return {'sumA': sum1, 'sumB': sum2}

    def calc_checksum(self,data):
        #data is passed in as the full packet minus the checksum bytes
        sumA = 0
        sumB = 0
        
        for i in range(2, len(data)):
            #python 2.7 : byte_val = ord(data[i])
            byte_val = data[i] if isinstance(data[i], int) else ord(data[i])
            sumA = (sumA + byte_val) % 255
            sumB = (sumB + sumA) % 255
            
        # print("Fletchers checksum A: ", sumA)
        # print("Fletchers checksum B: ", sumB)
        # print("Fletchers checksum A: 0x%02X" % sumA)
        # print("Fletchers checksum B: 0x%02X" % sumB)
        return {'sumA': sumA, 'sumB': sumB}

    def enum_bytes(self,data,name=''):
        # Troubleshooting function
        if name:
            print('~~~~~~~~~~~~  {}  ~~~~~~~~~~~~~~~~~~~~~'.format(name))
        else:
            print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
        
        
        #python2.7: print (' '.join(format(ord(char), '02x') for char in data) )
        print(' '.join(format(byte, '02x') for byte in data))
        print('~~~~~~~Byte Breakdown~~~~~~~~~~~~~~~~~~~~~~~~~~')
        
        for i, byte in enumerate(data):
            val = ord(byte) if isinstance(byte, str) else byte  # Python 2 vs 3 compatibility
            print("Byte %d: int=%3d, \\x%02X, 0x%02X" % (i + 1, val, val, val))
        print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')

    def packU8(self,value):
        return struct.pack('<B',value)
        
    def unpackU8(self,value):
        return struct.unpack('<B',value)[0]
        
    def packU16(self,value):
        return struct.pack('<I',value)
        
    def unpackU16(self,value):
        return struct.unpack('<I',value)[0]
        
    def packU32(self,value):
        return struct.pack('<Q',value)

    def unpackU32(self,value):
        return struct.unpack('<Q',value)[0]
    

    def read_data_packet(self,mclass,code,size,h_address,verbose=0):
        d_address = int(h_address)
        base_packet = struct.pack('<BBBBHH',self.sync1,self.sync2,mclass,code,size,d_address)

                #Calc and append checksum bytes
        cs_dict = self.calc_checksum(base_packet)
        self.packet = base_packet + self.packU8(cs_dict['sumA']) + self.packU8(cs_dict['sumB'])
        
        # for debugging
        if verbose:
            self.enum_bytes(self.packet, 'reading {}'.format(h_address))
        
        #send packet and recieve return packet
        rdata = self.send_packet(self.packet,1)
        
        #calc checksum for data in recvd packet
        cs_dict = self.calc_checksum(rdata[0:-2])
        
        # Unpack using struct & Assign to variables
        if h_address == 2048:
            fields = struct.unpack('<BBBBHHIBB', rdata)
        else:
            fields = struct.unpack('<BBBBHHfBB', rdata)
        sync1, sync2, class_, code, size, address, payload, checksumA, checksumB = fields
        
        # Print results
        if verbose:
            print("sync1:", sync1)
            print("sync2:", sync2)
            print("class:", class_)
            print("code:", code)
            print("size:", size)
            print("address:", address)
            print("payload:", payload)
            print("checksumA:", checksumA)
            print("checksumB:", checksumB)
        
        if address == d_address and cs_dict['sumA'] == checksumA and cs_dict['sumB'] == checksumB:
            if verbose:
                print ('Checksums match')
            return payload
        else:
            print ('Data Checksum Error')


    def send_async_data_request(self,mclass,code,size,h_address,verbose=0):
        d_address = int(h_address)
        base_packet = struct.pack('<BBBBHH',self.sync1,self.sync2,mclass,code,size,d_address)

                #Calc and append checksum bytes
        cs_dict = self.calc_checksum(base_packet)
        self.packet = base_packet + self.packU8(cs_dict['sumA']) + self.packU8(cs_dict['sumB'])
        
        # for debugging
        if verbose:
            self.enum_bytes(self.packet, 'reading {}'.format(h_address))
        
        #send packet and recieve return packet
        self.send_packet(self.packet,0)
        

    def send_packet(self,packet,wait_for_response = 1):

        if(self.tcpSock.send(packet)):    
            #print ('Sending message:',packet)

            # if wait_for_response:
                # rdata = self.tcpSock.recv(4096) 
                # self.tcpSock.close()
                # #rdata_ba = bytearray(rdata)
                # #return rdata_ba
                # return rdata

            #print ('Packet sent successfully: ', packet)
            pass
        else:
            print ('Error sending packet:',packet)

    
    def proportional_control(self,seek_az,seek_el):
    
        # print ('###########################################')
        # print ('###########################################')
        seek_result = False
        sm = trakka_rx_statemachine.trakka_rx_statemachine()
        
        while not seek_result: 
            seek_result = self.seek_az_el(seek_az,seek_el)
            
            #trick into working w/o tcp
            #self.current_az = self.current_az + self.current_az_rate
            #self.current_el = self.current_el + self.current_el_rate
            
            self.get_azimuth_status()
            self.get_elevation_status()
            
            #read tcp port, pass to statemachine
            rdata = self.tcpSock.recv(4096) 
            # self.tcpSock.close()
            sm.process_data(rdata)
            self.current_az = math.degrees(sm.azimuth)
            self.current_el = math.degrees(sm.elevation)
            
            
            
        # print ('###########################################')
        # print ('###########################################')
        # print ('seek complete')
        
        
    
    def seek_az_el(self,seek_az,seek_el):
        
        #determine difference and which direction to move
        az_diff = seek_az - self.current_az 
        el_diff = seek_el - self.current_el
        
        if abs(az_diff) > 180:
            if az_diff > 0:
                az_diff = az_diff - 360
            else:
                az_diff = az_diff + 360 
        
        if abs(az_diff) < self.exit_threshold_deg and abs(el_diff) < self.exit_threshold_deg:
            self.set_azimuth_rate(0)
            self.set_elevation_rate(0)
            return True
        
        
        
        az_rate = math.radians(az_diff) * self.gain
        el_rate = math.radians(el_diff) * self.gain
        
        if az_rate > self.rate_threshold:
            az_rate = self.rate_threshold
            
        if el_rate > self.rate_threshold:
            el_rate = self.rate_threshold
        
        # print ('Current AZ : ',self.current_az)
        # print ('Seek AZ    : ',seek_az)
        # print ('az diff    : ',az_diff)
        # print ('az rate    : ',az_rate)
        
        # print ('Current EL : ',self.current_el)
        # print ('Seek EL    : ',seek_el)
        # print ('el_diff    : ',el_diff)
        # print ('el_rate    : ',el_rate)
        
        self.set_azimuth_rate(az_rate)
        self.set_elevation_rate(el_rate)
        
        # send read AZ
        # send read EL
        
        return False

        
        

    # ------------------------------------------------------------------------------------------------------

    def get_gimbal_mode(self):
        # Read :CLASS 0x02, CODE 3 , SIZE : 2, ADDRESS 0x0800 (2048)
        h_address = 0x0800
        payload = self.read_data_packet(1,3,2,h_address)
        return payload

    def get_azimuth_status(self):
        #Page 13 : Gimbal  Angle AZ OA         0x1809 (6153)  Angle in radians    F32
        #CLASS : 1, CODE : 3, SIZE : 2
        h_address = 0x1809
        payload = self.send_async_data_request(1,3,2,h_address)


    def get_elevation_status(self):
        ## NEEDS PROPER CHECKSUM
        #Page 13 : Angle EL OA                 0x180A (6154)  Angle in radians    F32
        #CLASS : 1, CODE : 3, SIZE : 2
        h_address = 0x180A
        payload = self.send_async_data_request(1,3,2,h_address)
        
        
    def get_zoom_status(self,sensor):

        if sensor == 1:
            #Page 15 : Sensor 1   Digital Zoom Ratio      0x1101      Ratio from x1.0 up to sensor max ratio      F32
            h_address = 0x1101
        elif sensor == 2:
            #Page 15 : Sensor 2   Digital Zoom Ratio      0x1201      Ratio from x1.0 up to sensor max ratio      F32
            h_address = 0x1201
        elif sensor == 3:
            #Page 15 : Sensor 3   Digital Zoom Ratio      0x1401      Ratio from x1.0 up to sensor max ratio      F32
            h_address = 0x1401
        else: # DEFAULT IF NOT INDICATED sensor == 1
            sensor = 1
            h_address = 0x1101

        payload = self.read_data_packet(1,3,2,h_address)
        return payload



    # ********************************************************************************************************
    
    
    def set_gimbal_mode(self,mode):
        #Page 17 : #3.3.4. Set Mode
        # CLASS: 0x02 , CODE : 0x81 (129) , SIZE : 0x01 , VALUE (U8) Rate:0x00, Cage:0x01, Stow:0x02, Geo Point:0x03
        #Value should be 0, 1, 2, or 3
        base_packet = struct.pack('<BBBBHB',self.sync1,self.sync2,2,129,1,mode)

        #Calc and append checksum bytes
        cs_dict = self.calc_checksum(base_packet)
        self.packet = base_packet + self.packU8(cs_dict['sumA']) + self.packU8(cs_dict['sumB'])
        
        #For Debugging
        self.enum_bytes(self.packet, 'Set Gimbal Mode : {}'.format(mode))
        
        self.send_packet(self.packet,0)


    def set_azimuth_rate(self,value):
    
        self.current_az_rate = value
        ############################################################################### COMPLETE
        # NOTE: Set Mode (CLASS 0x02, CODE 0x81) to Rate (0) for this command to have effect.
        # CLASS: 0x02 , CODE: 0x02 ,  SIZE: 0x04  , Value: (F32) Angular rate in radians per second
        base_packet = struct.pack('<BBBBHf',self.sync1,self.sync2,2,2,4,value)

        #Calc and append checksum bytes
        cs_dict = self.calc_checksum(base_packet)
        self.packet = base_packet + self.packU8(cs_dict['sumA']) + self.packU8(cs_dict['sumB'])
        
        #For Debugging
        #self.enum_bytes(self.packet)
        
        self.send_packet(self.packet,0)

    def set_elevation_rate(self,value):
        self.current_el_rate = value
        ###############################################################################
        # CLASS: 0x02 ,  CODE: 0x03 , SIZE: 0x04 , Value: (F32) Angular rate in radians per second
        base_packet = struct.pack('<BBBBHf',self.sync1,self.sync2,2,3,4,value)

        #Calc and append checksum bytes
        cs_dict = self.calc_checksum(base_packet)
        self.packet = base_packet + self.packU8(cs_dict['sumA']) + self.packU8(cs_dict['sumB'])
        
        #For Debugging
        #self.enum_bytes(self.packet)
        
        self.send_packet(self.packet,0)
        
        
    def set_zoom_rate(self,sensor,command_word,value):
        ###############################################################################
        #Page27  :  3.6.2. Set Zoom
        # CLASS: 0x81 , CODE: 0x02 , SIZE: 0x06
        #Sensor Index (U8),  Zoom Command (U8),  Zoom Value (F32) ( see ICD for valid values)
        
        #[ ADD LOGIC TO CHECK IF ZOOM VALUE IS VALID PER COMMAND TYPE ]
        if command_word == 'RATE':
            command = 0
        elif command_word == 'HFOV':
            command = 1
        elif command_word == 'DZ_RATE':
            command = 2
        elif command_word == 'COMBINED':
            command = 3
        else:  #command_word == 'RATE':
            command = 0

        base_packet = struct.pack('<BBBBHBBf',self.sync1,self.sync2,129,2,6,sensor,command,value)

        #Calc and append checksum bytes
        cs_dict = self.calc_checksum(base_packet)
        self.packet = base_packet + self.packU8(cs_dict['sumA']) + self.packU8(cs_dict['sumB'])
        
        #For Debugging
        self.enum_bytes(self.packet, 'Set_Zoom_rate sent : {} : {}'.format(command_word,value))
        
        self.send_packet(self.packet,0)
        print ('Set_Zoom_rate sent : {} : {}'.format(command_word,value))
        

    # ********************************************************************************************************
    
    def setpoint_ecef(self, point_x, point_y, point_z):
        #NOTE for this to work Gimbal mode must be set to GeoPoint Mode (Gimbal Mode = 3)
        # Page 25  : 3.5.2   CLASS: 0x4 ,  CODE: 0x81 (129) , SIZE: 0x18 (24) , 
        # (F64) : ECEF X Coord ,  (F64) : ECEF Y Coord  ,  (F64) : ECEF Z Coord
        
        #                                     B          B          B B   H  d        d        d 
        base_packet = struct.pack('<BBBBHddd',self.sync1,self.sync2,4,129,24,point_x, point_y, point_z)

        #Calc and append checksum bytes
        cs_dict = self.calc_checksum(base_packet)
        self.packet = base_packet + self.packU8(cs_dict['sumA']) + self.packU8(cs_dict['sumB'])
        
        #For Debugging
        self.enum_bytes(self.packet, 'SetPoint ECEF to {}|{}|{}'.format(point_x, point_y, point_z))
        
        self.send_packet(self.packet,0)
        
        
    def geopoint_command(self,command):
        # Page 25  : 3.5.3   CLASS: 0x4 ,  CODE: 0x8A (138) , SIZE: 0x01 , Data (U8) Start: 0x00, Toggle: 0x01
        #                                   B          B          B B   H B 
        base_packet = struct.pack('<BBBBHB',self.sync1,self.sync2,4,138,1,command)

        #Calc and append checksum bytes
        cs_dict = self.calc_checksum(base_packet)
        self.packet = base_packet + self.packU8(cs_dict['sumA']) + self.packU8(cs_dict['sumB'])
        
        #For Debugging
        self.enum_bytes(self.packet, 'Geopoint Command Packet')
        
        self.send_packet(self.packet,0)
       
    # ********************************************************************************************************
    def modify_mtir(self,command,sensor,parameter_x,parameter_y):
        #Page 34: 3.7.3 :  CLASS: 0x82 (130) ,  CODE: 0x02 , SIZE: 0x03 , Command (U8), parameter (S16)
        # 0:0, 1 : 0-128, 2:-1, +1, 3:0+, 4:0+
        #                                      B          B          B   B H B       B      h           h
        base_packet = struct.pack('<BBBBHBBhh',self.sync1,self.sync2,130,2,3,command,sensor,parameter_x,parameter_y)

        #Calc and append checksum bytes
        cs_dict = self.calc_checksum(base_packet)
        self.packet = base_packet + self.packU8(cs_dict['sumA']) + self.packU8(cs_dict['sumB'])
        
        #For Debugging
        self.enum_bytes(self.packet)
        
        self.send_packet(self.packet,0)
        
    def modify_mti(self,command,value):
        #Page 34: 3.7.3 :  CLASS: 0x82 (130) ,  CODE: 0x03 , SIZE: 0x03 , Command (U8), parameter (S16)
        # 0:0, 1 : 0-128, 2:-1, +1, 3:0+, 4:0+
        #                                      B          B          B   B H B       B      h           h
        base_packet = struct.pack('<BBBBHBh',self.sync1,self.sync2,130,3,3,command,value)

        #Calc and append checksum bytes
        cs_dict = self.calc_checksum(base_packet)
        self.packet = base_packet + self.packU8(cs_dict['sumA']) + self.packU8(cs_dict['sumB'])
        
        #For Debugging
        self.enum_bytes(self.packet)
        
        self.send_packet(self.packet,0)



    def video_track_data(self):
        #Page 37: 3.7.7  CLASS: 0x82 (130) ,  CODE: 0x07 , SIZE: 0x05 (15) 
        # Source (U8) : Sensor 0-4 , Track Index (U16) : ID , 
        #Tracker Status (U8): Bit0: 1=Active Track, 0=Inactive : Bit1 : 1=Coasting, 0=Not Coasting
        #Track Quality (U8): 0-100% Quality, 
        #Track Error AZ (F32): AZ Angular error from center in radians
        #Track Error EL (F32): EL Angular error from center in radians
        #Track Type (U8) : 0:Unknown, 1:Rotary ac/drone, 2:fixed wing ac/drone, 3:Vehicle, 4:person, 5:boat
        #Track type confidence(U8) : 0-100% confidence
        
        # These are sent at intervals from the camera
        # How are these read? does modify_mti need to be sent in order to recieve this?
        pass

    # **********************************************************************
    
    def wgs84_to_egm96(self,x,y,z):

        transformer = Transformer.from_crs(
            "EPSG:4979",       # WGS84 with ellipsoidal height
            "EPSG:4326+5773",  # WGS84 with EGM96 geoid height
            always_xy=True
        )

        #print('Longitude: {}, Latitude: {}, Height (EGM96): {}'.format(x, y, z))
        # Perform the transformation
        lon_out, lat_out, egm96_elevation = transformer.transform(x, y, z)
        geoid_difference = z - egm96_elevation
        #return egm96_elevation, geoid_difference
        #print ('Diff: {}'.format(geoid_difference))
        #print ('96EL: {}'.format(egm96_elevation))

        #print('Longitude: {}, Latitude: {}, Height (HAE)  : {}'.format(lon_out,lat_out, egm96_elevation))
        return(lon_out,lat_out, egm96_elevation)

    def lla_to_ecef(self,lla_x,lla_y,lla_z):
        # Define the transformer from LLA (EPSG:4326) to ECEF (EPSG:4978)
        transformer = Transformer.from_crs("epsg:4326", "epsg:4978", always_xy=True)

        #print('LLA Longitude: {}, LLA Latitude: {}, LLA Height : {}'.format(lla_x, lla_y, lla_z))

        # Convert to ECEF
        ecef_x, ecef_y, ecef_z = transformer.transform(lla_x, lla_y, lla_z)

        #print(f"ECEF Coordinates: X={ecef_x}, Y={ecef_y}, Z={ecef_z}")
        return ecef_x, ecef_y, ecef_z
    
    # ---------------------- ABSOLUTE POINTING (CAGE) ----------------------
    # These two wrappers send absolute setpoints (in radians) to the gimbal.
    # REQUIREMENT: Set gimbal mode to CAGE (1) before using these:
    #   self.set_gimbal_mode(1)
    # RATIONALE: Rate jogs are nondeterministic for sweeps. Absolute AZ/EL
    # allows repeatable bearing-based searches and waypoint scanning.

    def set_cage_az(self, az_rad: float) -> None:
        """
        Set absolute azimuth (radians) in CAGE mode.
        ICD: CLASS 0x02 (Gimbal), CODE 0x82 (Set Cage AZ), SIZE 0x0004 (F32)
        Payload: float32 radians
        """
        base_packet = struct.pack('<BBBBHf', self.sync1, self.sync2, 0x02, 0x82, 0x0004, az_rad)
        cs = self.calc_checksum(base_packet)
        self.packet = base_packet + self.packU8(cs['sumA']) + self.packU8(cs['sumB'])
        # self.enum_bytes(self.packet, 'Set Cage AZ')  # uncomment for debug
        self.send_packet(self.packet, 0)

    def set_cage_el(self, el_rad: float) -> None:
        """
        Set absolute elevation (radians) in CAGE mode.
        ICD: CLASS 0x02 (Gimbal), CODE 0x83 (Set Cage EL), SIZE 0x0004 (F32)
        Payload: float32 radians
        """
        base_packet = struct.pack('<BBBBHf', self.sync1, self.sync2, 0x02, 0x83, 0x0004, el_rad)
        cs = self.calc_checksum(base_packet)
        self.packet = base_packet + self.packU8(cs['sumA']) + self.packU8(cs['sumB'])
        # self.enum_bytes(self.packet, 'Set Cage EL')  # uncomment for debug
        self.send_packet(self.packet, 0)
