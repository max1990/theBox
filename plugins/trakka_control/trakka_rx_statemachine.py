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

##########################################################################
#
#  This is a python 3 class for sending tcp packets to the Trakka camera.
#  As of 2025-09-05 it has only been tested with the simulator.
#  
#  2025-09-05 PB
#
##########################################################################


class trakka_rx_statemachine:

    _packet = bytearray()
    _state = 'SOM1'
    _size = 0;
    _suma = 0;
    _sumb = 0;

    azimuth = 0.0
    elevation  = 0.0

    sync1 = 167
    sync2 = 84

    def process_data(self,data):
        for i in range(0, len(data)):
            self.process_byte(data[i]);

    def process_byte(self,data):

        self._packet.append(data);
        
        if self._state == 'SOM1':
            if data == self.sync1:
                self._state = 'SOM2'
                
        elif self._state =='SOM2':
            if data == self.sync2:
                self._state = 'CLASS'
            else:
                self._packet.clear()
                self._state = 'SOM1'
    
        elif self._state == 'CLASS':
            self._state = 'CODE'

        elif self._state == 'CODE':
            self._state = 'SIZE1'

        elif self._state == 'SIZE1':
            self._state = 'SIZE2'

        elif self._state == 'SIZE2':
            self._size = struct.unpack('<H',self._packet[4:6])[0]
            if self._size == 0:
                self._state = 'CSUMA'
            else:
                self._state = 'DATA'

        elif self._state == 'DATA':
            if len(self._packet) >= self._size+6:
                self._state = 'CSUMA'

        elif self._state == 'CSUMA':
            self._suma = data
            self._state = 'CSUMB'

        elif self._state == 'CSUMB':
            self._sumb = data;
            ra,rb = self.calc_checksum(self._packet[:-2])
            if ra == self._suma and rb == self._sumb:
                self.process_packet()
            
            self._state = 'SOM1'
            self._packet.clear()
        
        else:
            self._state = 'SOM1'
            self._packet.clear()

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
        #return {'sumA': sumA, 'sumB': sumB}
        return (sumA,sumB)

    def process_packet(self):

        print (self._packet.hex())
        klass = self._packet[2];
        code = self._packet[3];
        size = struct.unpack('<H',self._packet[4:6])[0]
        
        # database reads:
        if code == 0x04 and klass == 0x01 and size == 6:
            addr = struct.unpack('<H',self._packet[6:8])[0]
            vfloat = struct.unpack('<f',self._packet[8:12])[0]

            if addr == 0x1809:  #az
                self.azimuth = vfloat
            elif addr == 0x180A: #el
                self.elevation = vfloat
        
        
        # MTI/Tracks            # only send messages once the camera is at it's terminal destination to not get spurrious detections on the way to the commanded bearing
        if code == 0x07 and klass == 0x82 and size >= 15:
            print("=====TRACK====")
            print(" SRC: ", self._packet[6] )
            print(" IDX: ", struct.unpack('<H',self._packet[7:9])[0] )
            print(" CNF: ", self._packet[10] )
            print(" TYP: ", self._packet[19] )
            print(" TTC: ", self._packet[20] )
    

