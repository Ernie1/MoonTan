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

# Initialize logger
logging.basicConfig(
    format=
    '%(asctime)s,%(msecs)03d - %(levelname)s - %(funcName)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.NOTSET)
logger = logging.getLogger()


class LFTPClient(object):
    def __init__(self, command, serverAddress, filename):
        self.running = False
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.serverAddress = serverAddress
        self.file = open(filename, 'rb')
        self.NextSeqNum = random.randint(1000, 10000)
        self.duplicateAck = 0
        # self.rwnd doesn't contains the length of segment header for convenient
        self.rwnd = 0
        self.TimeoutInterval = 1.0
        self.TimeStart = time.time()
        # SYN
        self.SndBuffer = [[
            self.NextSeqNum,
            self.toHeader(seqNum=self.NextSeqNum, sf=1) + json.dumps(
                {
                    'command': command,
                    'filename': filename
                }).encode(), False
        ]]  # [[SeqNum, Segment, Sent]]
        # Multithreading
        self.lock = threading.Lock()
        self.pool = [
            threading.Thread(target=f) for f in [
                self.fillSndBuffer, self.castSndBuffer, self.rcvAckAndRwnd,
                self.detectTimeout, self.detectDuplicateAck, self.slideWindow
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
            # Suppose MTU is 576, length of UDP header is 8, then MSS is 576 - 20 - 8 = 548
            # Here use 536 as same as TCP
            # Suppose capacity of self.SndBuffer is 65536 bytes, 65536 / 576 roughly 113 segments
            if len(self.SndBuffer) < 113:
                segment = self.file.read(536)
                self.lock.acquire()
                seqNum = self.SndBuffer[-1][0] + len(
                    self.SndBuffer[-1][1]) - 12
                if len(segment) == 0:
                    # FIN, '0' is placeholder
                    self.SndBuffer.append([
                        seqNum,
                        self.toHeader(seqNum=seqNum, sf=2) + b'0', False
                    ])
                    self.lock.release()
                    break
                self.SndBuffer.append(
                    [seqNum,
                     self.toHeader(seqNum=seqNum) + segment, False])
                self.lock.release()

    def castSndBuffer(self):
        while self.running:
            self.lock.acquire()
            if len(self.SndBuffer) and self.SndBuffer[0][0] != self.NextSeqNum:
                self.SndBuffer.pop(0)
                if len(self.SndBuffer) == 0:
                    self.running = False
                    self.file.close()
                    self.socket.close()
                    logger.info('Finished')
            self.lock.release()

    def rcvAckAndRwnd(self):
        while self.running:
            self.lock.acquire()
            segment = self.socket.recvfrom(1024)[0]
            _, ackNum, _, _, rwnd = self.fromHeader(segment)
            if ackNum == self.NextSeqNum:
                self.duplicateAck += 1
            else:
                self.NextSeqNum = ackNum
                self.duplicateAck = 1
            self.TimeStart = time.time()
            self.rwnd = rwnd
            self.lock.release()

    def retransmission(self):
        # self.lock.acquire() 
        print(len(self.SndBuffer))
        for segment in self.SndBuffer:
            # With the help of self.castSndBuffer, it should be self.SndBuffer[0]
            if segment[0] == self.NextSeqNum:
                self.socket.sendto(segment[1], self.serverAddress)
                self.TimeStart = time.time()
                self.duplicateAck = 1
                logger.info('Sequence number:{0}'.format(self.NextSeqNum))
                break
        # self.lock.release()

    def detectTimeout(self):
        while self.running:
            self.lock.acquire() 
            if time.time() - self.TimeStart > self.TimeoutInterval:
                logger.warning('Sequence number:{0}'.format(self.NextSeqNum))
                self.retransmission()
            self.lock.release()

    def detectDuplicateAck(self):
        while self.running:
            self.lock.acquire() 
            if self.duplicateAck > 2:
                logger.warning('Sequence number:{0}'.format(self.NextSeqNum))
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
    print(serverAddress)
    filename = sys.argv[3]
    print(filename)
    logger.info('Command:{0} Address:{1} File:{2}'.format(
        sys.argv[1], serverAddress, filename))
    return sys.argv[1], serverAddress, filename


if __name__ == "__main__":
    client = LFTPClient(*parseParameter())
    client.start()