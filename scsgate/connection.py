""" This module contains an helper class to initiate a connection
with the SCSGate device """

"""import serial as pyserial"""
import socket
class Connection:

    """ Connection to SCSGate device """

    def __init__(self, device, logger, port):
        """ Initialize the class

        Arguments:
        device: string containing the serial device allocated to SCSGate
        logger: instance of logging
        """
        """self._serial = pyserial.Serial(device, 115200)"""
        self.device = device
        self.logger = logger
        self.port = port
        if port != 0:
            try:
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self._socket.settimeout(1)
            except socket.error:
                raise RuntimeError("Failed to create sockt")
        else:
            self._socket = pyserial.Serial(device, 115200)

        logger.info("Clearing buffers")
        """self._serial.write(b"@b")"""
        """self._socket.sendto(b"@b", (device, port))"""
        self.send(b"@b")
        """ret = self._serial.read(1)"""
        ret = self.receive()
        """ret = self._socket.recvfrom(1);"""
        if ret != b"k":
            raise RuntimeError("Error while clearing buffers")

        # ensure pending operations are terminated (eg: @r, @l)
        """self._serial.write(b"@c")"""
        """self._socket.sendto(b"@c", (device, port))"""
        """ret = self._serial.read()"""
        """ret = self._socket.recvfrom(1);"""
        self.send(b"@c")
        ret = self.receive()
        if ret != b"k":
            raise RuntimeError("Error while cancelling pending operations")

        logger.info("Enabling ASCII mode")
        """self._serial.write(b"@MA")"""
        """self._socket.sendto(b"@MA", (device, port))"""
        """ret = self._serial.read(1)"""
        """ret = self._socket.recvfrom(1);"""
        self.send(b"@MA")
        ret = self.receive()
        if ret != b"k":
            raise RuntimeError("Error while enabling ASCII mode")

        logger.info("Filter Ack messages")
        """self._serial.write(b"@F2")"""
        """self._socket.sendto(b"@F2", (device, port))"""
        """ret = self._serial.read(1)"""
        """ret = self._socket.recvfrom(1);"""
        self.send(b"@F2")
        ret = self.receive()
        if ret != b"k":
            raise RuntimeError("Error while setting filter")

    @property
    def serial(self):
        """ Returns the pyserial.Serial instance """
        return self._socket

    def close(self):
        """ Closes the connection to the serial port and ensure no pending
        operatoin are left """
        """self._serial.write(b"@c")"""
        self._socket.sendto(b"@c", ("192.168.1.26", 52056))
        """self._serial.read()"""
        self._socket.recvfrom(1);
        """self._serial.close()"""

    def send(self, message):
        if self.port != 0:
            self._socket.sendto(message, (self.device, self.port))
        else:
            self._serial.write(message)

    def receive(self):
        ret = None
        if self.port != 0:
            try:    
                ret = self._socket.recvfrom(1024);
            except socket.timeout:
                self.logger.info("Socket Timeout")
                return
        else:
            lenght = int(self._socket.read(), 16)
            if lenght == b'k':
                return lenght
            else:
                data = self._socket.read(lenght * 2)
                return lenght + data
        return ret[0]
