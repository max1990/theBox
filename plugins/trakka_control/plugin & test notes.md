# tcp_tester.py Notes:

## Enable & Receive Drone Detection Messages

### Enable
- this must be sent to enable data return
```python

	print ('----------------------------- Enable and receive Drone Identification Messages ')
	s.modify_mti(4,30)
```
  
  

### Receive Data & Start the Drone Detection System
- this listens to messages from the camera
- this needs to be implemented gracefully since it outputs what it sees

```python
	sm = trakka_rx_statemachine.trakka_rx_statemachine()
	while True:
    	try:
        	s.get_azimuth_status()
        	rdata = s.tcpSock.recv(4096) 
        	# self.tcpSock.close()
        	sm.process_data(rdata)
    	except socket.timeout:
        	pass
	print ('----------------------------- Enable and recieve Drone Identification Messages ')
```



## Proportional Control Mode
- sets it to rate mode
- calls the ability to slew
- **NOTE: this blocks until the camera reaches it**  
	**we should set something to not listen to returns until the camera reaches the location**  
	**because the drone detector will still return detections during the slew command**
```python
	print ('----------------------------- Proportional Control ')

	starting at 0,0

	s.set_gimbal_mode(0)                                        # set to rate mode
	print ('---------------------------------')
	# calls the ability to slew the camera
	# blocks until the camera reaches the commanded location
	s.proportional_control(16,67)

	print ('----------------------------- Proportional Control ')
```

# tcp_sender.py Notes:

## Camera Commands
```python
    # speed of movement (deg/sec * gain * error %)
	gain = 2.5
	# max slew rate (60 is max)
    rate_threshold = 30
	# how close before we say stop (0.1 degree)
    exit_threshold_deg  = .1          

    exit_threshold_rad = math.radians(exit_threshold_deg)   # same as above
```