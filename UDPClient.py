# Programming UDP with the terminology and idea of TCP
# Suppose the size of file is less than 4294967296 bytes
# Suppose file exists and filename is unique
import socket
import sys
import logging
import json
import random
import threading
import time
import os

# Initialize logger
logging.basicConfig(
    format=
    '%(asctime)s,%(msecs)03d - %(levelname)s - %(funcName)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.NOTSET)
logger = logging.getLogger()


class LFTPClient(object):
    def __init__(self, command, serverAddress, filename, MSS):
        self.running = False
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.serverAddress = serverAddress
        self.file = open(filename, 'rb')
        self.fileSize = os.path.getsize(filename)
        self.MSS = MSS
        # Suppose capacity of self.SndBuffer is 65536 bytes, roughly floor( 65536 / self.MSS ) segments
        self.SndBufferCapacity = int(65536 / self.MSS)
        self.initSeqNum = random.randint(1000, 10000)
        self.NextSeqNum = self.initSeqNum
        self.NextByteFill = self.initSeqNum
        self.progress = 1
        self.duplicateAck = 0
        # self.rwnd doesn't contains the length of segment header for convenient
        self.rwnd = 0
        self.TimeoutInterval = 1.0
        self.TimeStart = time.time()
        # SYN
        self.SndBuffer = [[
            self.NextByteFill,
            self.toHeader(seqNum=self.NextSeqNum, sf=1) + json.dumps(
                {
                    'command': command,
                    'filename': filename
                }).encode(), False
        ]]  # [[SeqNum, Segment, Sent]]
        self.NextByteFill += len(self.SndBuffer[0][1]) - 12
        # Multithreading
        self.lock = threading.Lock()
        self.pool = [
            threading.Thread(target=f) for f in [
                self.fillSndBuffer, self.rcvAckAndRwnd, self.detectTimeout,
                self.slideWindow
            ]
        ]

    def start(self):
        self.running = True
        for t in self.pool:
            t.start()
        logger.info('Start')

    def toHeader(self, seqNum=0, ackNum=0, ack=0, sf=0, rwnd=0):
        return seqNum.to_bytes(
            4, byteorder="little") + ackNum.to_bytes(
                4, byteorder="little") + ack.to_bytes(
                    1, byteorder="little") + sf.to_bytes(
                        1, byteorder="little") + rwnd.to_bytes(
                            2, byteorder="little")

    def fromHeader(self, segment):
        return int.from_bytes(
            segment[:4], byteorder="little"), int.from_bytes(
                segment[4:8], byteorder="little"), int.from_bytes(
                    segment[8:9], byteorder="little"), int.from_bytes(
                        segment[9:10], byteorder="little"), int.from_bytes(
                            segment[10:12], byteorder="little")

    def fillSndBuffer(self):
        while self.running:
            self.lock.acquire()
            if len(self.SndBuffer) < self.SndBufferCapacity:
                segment = self.file.read(self.MSS)
                if len(segment) == 0:
                    self.file.close()
                    # FIN, '0' is placeholder
                    self.SndBuffer.append([
                        self.NextByteFill,
                        self.toHeader(seqNum=self.NextByteFill, sf=2) + b'0',
                        False
                    ])
                    self.lock.release()
                    break
                self.SndBuffer.append([
                    self.NextByteFill,
                    self.toHeader(seqNum=self.NextByteFill) + segment, False
                ])
                self.NextByteFill += len(self.SndBuffer[-1][1]) - 12
            self.lock.release()

    def rcvAckAndRwnd(self):
        while self.running:
            segment = self.socket.recvfrom(self.MSS + 12)[0]
            self.lock.acquire()
            _, ackNum, _, _, rwnd = self.fromHeader(segment)
            if ackNum == self.NextSeqNum:
                self.duplicateAck += 1
                # Detect duplicate ack
                if self.duplicateAck > 2:
                    logger.warning('Duplicate ack sequence number:{0}'.format(
                        self.NextSeqNum))
                    self.retransmission()
            elif ackNum > self.NextSeqNum:
                self.NextSeqNum = ackNum
                self.duplicateAck = 1
                # Show progress
                progress = self.progress
                while (
                        self.NextSeqNum - self.initSeqNum
                ) / self.fileSize >= self.progress * 0.05:
                    self.progress += 1
                if progress < self.progress:
                    logger.info('Sent {0}%'.format((self.progress - 1) * 5))
                # Cast out from self.SndBuffer
                while len(self.SndBuffer
                          ) and self.SndBuffer[0][0] < self.NextSeqNum:
                    s = self.SndBuffer.pop(0)
                    # Determine whether last cast out is FIN
                    if len(self.SndBuffer) == 0 and self.fromHeader(s[1])[3] == 2:
                        self.running = False
                        self.socket.close()
                        logger.info('Finished')
            self.rwnd = rwnd
            self.TimeStart = time.time()
            self.lock.release()

    def retransmission(self):
        for segment in self.SndBuffer:
            if segment[0] == self.NextSeqNum:
                self.socket.sendto(segment[1], self.serverAddress)
                self.TimeStart = time.time()
                self.duplicateAck = 1
                logger.info('Sequence number:{0}'.format(self.NextSeqNum))
                break

    def detectTimeout(self):
        while self.running:
            self.lock.acquire()
            if time.time() - self.TimeStart > self.TimeoutInterval:
                logger.warning('Sequence number:{0}, {1}'.format(
                    self.NextSeqNum, len(self.SndBuffer)))
                self.retransmission()
            self.lock.release()

    def slideWindow(self):
        while self.running:
            self.lock.acquire()
            for i in range(len(self.SndBuffer)):
                # Flow control
                if self.SndBuffer[i][2] == False and self.SndBuffer[i][
                        0] - self.NextSeqNum <= self.rwnd:
                    self.socket.sendto(self.SndBuffer[i][1],
                                       self.serverAddress)
                    self.TimeStart = time.time()
                    self.SndBuffer[i][2] = True
                elif self.SndBuffer[i][2] == False:
                    break
            self.lock.release()


def parseParameter():
    # Sending file should use the following format
    #   LFTP lsend servername:serverport mylargefile
    # Getting file should use the following format
    #   LFTP lget servername:serverport mylargefile
    serverName, serverPort = sys.argv[2].split(':')
    serverAddress = (serverName, int(serverPort))
    filename = sys.argv[3]
    logger.info('Command:{0} Address:{1} File:{2}'.format(
        sys.argv[1], serverAddress, filename))
    return sys.argv[1], serverAddress, filename


if __name__ == "__main__":
    client = LFTPClient(*parseParameter(), 5360)
    client.start()