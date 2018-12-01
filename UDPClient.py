# Programming UDP with the terminology and idea of TCP
# 暂时不考虑超过 4294967296 bytes 的文件
import socket
import sys
import logging
import json
import random
import select
import threading
import time

# Initialize logger
logging.basicConfig(
    format='%(asctime)s,%(msecs)03d - %(levelname)s - %(funcName)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.NOTSET)
logger = logging.getLogger()


# 87380、16384
class LFTPClient(object):
    def __init__(self, command, serverAddress, filename):
        self.finished = False
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.serverAddress = serverAddress
        self.file = open(filename, 'rb')
        self.NextSeqNum = random.randint(1000, 10000)
        self.duplicateAck = 0
        # Dual purpose
        self.rwnd = 0
        self.TimeoutInterval = 1
        self.TimeStart = time
        # SYN
        self.SndBuffer = [(
            self.NextSeqNum,
            # '0' is placeholder
            self.toHeader(seqNum=self.NextSeqNum, sf=1) + b'0',
            False)]  # (SeqNum, Segment, Sent)
        # Multithreading
        self.lock = threading.Lock()
        self.pool = [
            threading.Thread(target=f) for f in [
                self.fillSndBuffer, self.castSndBuffer, self.rcvAckAndRwnd,
                self.detectTimeout, self.detectDuplicateAck, self.slideWindow
            ]
        ]

    def start(self):
        for t in self.pool:
            t.start()

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
        while True:
            # Suppose MTU is 576, length of UDP header is 8, then MSS is 576 - 8 = 568
            # But here use 536 as same as TCP
            # Suppose capacity of SndBuffer is 16384 bytes, 16384 / 536 roughly 30 segments
            # 这里可能有点小导致流控制作用不大
            if len(self.SndBuffer) < 30:
                segment = self.file.read(536)
                self.lock.acquire()
                seqNum = self.SndBuffer[-1][0] + len(
                    self.SndBuffer[-1][1]) - 12
                if len(segment) == 0:
                    # FIN
                    self.SndBuffer.append(
                        (seqNum, self.toHeader(seqNum=seqNum, sf=2) + b'0',
                         False))
                    self.lock.release()
                    break
                self.SndBuffer.append(
                    (seqNum, self.toHeader(seqNum=seqNum) + segment, False))
                self.lock.release()
            if self.finished:
                break

    def castSndBuffer(self):
        while True:
            if self.SndBuffer[0][0] != self.NextSeqNum:
                self.lock.acquire()
                self.SndBuffer.pop(0)
                if len(self.SndBuffer) == 0:
                    self.socket.close()
                    self.finished = True
                    logger.info('Finished')
                self.lock.release()
            if self.finished:
                break

    def rcvAckAndRwnd(self):
        while True:
            segment = self.socket.recvfrom(1024)[0]
            header = self.fromHeader(segment)
            self.lock.acquire()
            if header[1] == self.NextSeqNum:
                self.duplicateAck += 1
            else:
                self.NextSeqNum = header[1]
                self.duplicateAck = 1
            self.TimeStart = time.time()
            self.rwnd = header[4]
            self.lock.release()
            if self.finished:
                break

    def retransmission(self):
        self.lock.acquire()
        for segment in self.SndBuffer:
            if segment[0] == self.NextSeqNum:
                self.socket.sendto(segment[1], self.serverAddress)
                self.TimeStart = time.time()
                self.duplicateAck = 1
                logger.info('Sequence number:{0}'.format(self.NextSeqNum))
                self.lock.release()
                break
        self.lock.release()

    def detectTimeout(self):
        while True:
            if time.time() - self.TimeStart > self.TimeoutInterval:
                logger.warn('Sequence number:{0}'.format(self.NextSeqNum))
                self.retransmission()
            if self.finished:
                break

    def detectDuplicateAck(self):
        while True:
            if self.duplicateAck > 2:
                logger.warn('Sequence number:{0}'.format(self.NextSeqNum))
                self.retransmission()
            if self.finished:
                break

    def slideWindow(self):
        while True:
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
            if self.finished:
                break


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