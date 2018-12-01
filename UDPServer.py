# Programming UDP with the terminology and idea of TCP
# Suppose the size of file is less than 4294967296 bytes
# Suppose no duplicate filenames
import socket
import logging
import json
import random
import threading
import time

# Initialize logger
logging.basicConfig(
    format='%(asctime)s,%(msecs)03d - %(levelname)s - %(funcName)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.NOTSET)
logger = logging.getLogger()


def toHeader(seqNum=0, ackNum=0, ack=0, sf=0, rwnd=0):
    return seqNum.to_bytes(
        4, byteorder="little") + ackNum.to_bytes(
            4, byteorder="little") + ack.to_bytes(
                1, byteorder="little") + sf.to_bytes(
                    1, byteorder="little") + rwnd.to_bytes(
                        2, byteorder="little")


def fromHeader(segment):
    return int.from_bytes(
        segment[:4], byteorder="little"), int.from_bytes(
            segment[4:8], byteorder="little"), int.from_bytes(
                segment[8:9], byteorder="little"), int.from_bytes(
                    segment[9:10], byteorder="little"), int.from_bytes(
                        segment[10:12], byteorder="little")


class LFTPServer(object):
    # self, command, clientAddress, filename
    def __init__(self, clientAddress):
        self.finished = False
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.clientAddress = clientAddress

        # self.file = open(filename, 'rb')

        # self.NextSeqNum = random.randint(1000, 10000)
        # self.duplicateAck = 0
        # self.rwnd doesn't contains the length of segment header for convenient
        self.rwnd = 0
        # self.TimeoutInterval = 1
        # self.TimeStart = time
        # SYN
        # self.SndBuffer = [(
        #     self.NextSeqNum,
        #     # '0' is placeholder
        #     toHeader(seqNum=self.NextSeqNum, sf=1) + b'0',
        #     False)]  # [(SeqNum, Segment, Sent)]

        self.RcvBuffer = []  # [(SeqNum, Data, sf)]

        # Multithreading
        # self.lock = threading.Lock()
        # self.pool = [
        #     threading.Thread(target=f) for f in [
        #         self.fillSndBuffer, self.castSndBuffer, self.rcvAckAndRwnd,
        #         self.detectTimeout, self.detectDuplicateAck, self.slideWindow
        #     ]
        # ]

    # def start(self):
    #     for t in self.pool:
    #         t.start()

    # def fillSndBuffer(self):
    #     while True:
    #         # Suppose MTU is 576, length of UDP header is 8, then MSS is 576 - 8 = 568
    #         # Here use 536 as same as TCP
    #         # Suppose capacity of SndBuffer is 16384 bytes, 16384 / 536 roughly 30 segments
    #         # 这里可能有点小导致流控制作用不大
    #         if len(self.SndBuffer) < 30:
    #             segment = self.file.read(536)
    #             self.lock.acquire()
    #             seqNum = self.SndBuffer[-1][0] + len(
    #                 self.SndBuffer[-1][1]) - 12
    #             if len(segment) == 0:
    #                 # FIN
    #                 self.SndBuffer.append(
    #                     (seqNum, toHeader(seqNum=seqNum, sf=2) + b'0',
    #                      False))
    #                 self.lock.release()
    #                 break
    #             self.SndBuffer.append(
    #                 (seqNum, toHeader(seqNum=seqNum) + segment, False))
    #             self.lock.release()
    #         if self.finished:
    #             break

    # def castSndBuffer(self):
    #     while True:
    #         if len(self.SndBuffer) and self.SndBuffer[0][0] != self.NextSeqNum:
    #             self.lock.acquire()
    #             self.SndBuffer.pop(0)
    #             if len(self.SndBuffer) == 0:
    #                 self.socket.close()
    #                 self.finished = True
    #                 logger.info('Finished')
    #             self.lock.release()
    #         if self.finished:
    #             break

    # def rcvAckAndRwnd(self):
    #     while True:
    #         segment = self.socket.recvfrom(1024)
    #         header = fromHeader(segment)
    #         self.lock.acquire()
    #         if header[1] == self.NextSeqNum:
    #             self.duplicateAck += 1
    #         else:
    #             self.NextSeqNum = header[1]
    #             self.duplicateAck = 1
    #         self.TimeStart = time.time()
    #         self.rwnd = header[4]
    #         self.lock.release()
    #         if self.finished:
    #             break

    def rcvSegment(self, segment):
        # self.lock.acquire()
        # seqNum, ackNum, ack, sf, rwnd
        seqNum, _, _, sf, _ = fromHeader(segment)
        data = segment[12:]
        # SYN
        if sf == 1:
            # command ???
            info = json.loads(data.decode())
            self.file = open(info['filename'], 'wb')
            logger.info('Start to receive {0} from {1}'.format(
                info['filename'], self.clientAddress))
            self.NextSeqNum = seqNum + len(data)
        else:
            i = 0
            while i < len(self.RcvBuffer) and self.RcvBuffer[i][0] < seqNum:
                i += 1
            # Determine whether duplicate
            if len(self.RcvBuffer) == 0 or self.RcvBuffer[i][0] != seqNum:
                self.RcvBuffer.insert(i, (seqNum, data, sf))
                # Cast out from self.RcvBuffer
                i = 0
                while i < len(self.RcvBuffer
                              ) and self.NextSeqNum == self.RcvBuffer[i][0]:
                    self.NextSeqNum += len(self.RcvBuffer[i][1])
                    # FIN
                    if self.RcvBuffer[i][2] == 2:
                        self.file.close()
                        self.socket.sendto(
                            toHeader(
                                ackNum=self.NextSeqNum,
                                ack=1,
                                sf=2,
                                rwnd=(151 - len(self.RcvBuffer)) * 536),
                            self.clientAddress)
                        self.socket.close()
                        logger.info('{0} finished'.format(self.clientAddress))
                        self.finished = True
                    else:
                        self.file.write(self.RcvBuffer[i][1])
                    i += 1
                self.RcvBuffer = self.RcvBuffer[i:]
        # ACK
        # Suppose capacity of self.RcvBuffer is 87380 bytes, 87380 / 576 roughly 151 segments
        self.socket.sendto(
            toHeader(
                ackNum=self.NextSeqNum,
                ack=1,
                sf=0,
                rwnd=(151 - len(self.RcvBuffer)) * 536), self.clientAddress)
        # self.lock.release()

    # def retransmission(self):
    #     self.lock.acquire()
    #     for segment in self.SndBuffer:
    #         if segment[0] == self.NextSeqNum:
    #             self.socket.sendto(segment[1], self.clientAddress)
    #             self.TimeStart = time.time()
    #             self.duplicateAck = 1
    #             logger.info('Sequence number:{0}'.format(self.NextSeqNum))
    #             self.lock.release()
    #             break
    #     self.lock.release()

    # def detectTimeout(self):
    #     while True:
    #         if time.time() - self.TimeStart > self.TimeoutInterval:
    #             logger.warn('Sequence number:{0}'.format(self.NextSeqNum))
    #             self.retransmission()
    #         if self.finished:
    #             break

    # def detectDuplicateAck(self):
    #     while True:
    #         if self.duplicateAck > 2:
    #             logger.warn('Sequence number:{0}'.format(self.NextSeqNum))
    #             self.retransmission()
    #         if self.finished:
    #             break

    # def slideWindow(self):
    #     while True:
    #         self.lock.acquire()
    #         for i in range(len(self.SndBuffer)):
    #             # Flow control
    #             if self.SndBuffer[i][2] == False and self.SndBuffer[i][
    #                     0] - self.NextSeqNum <= self.rwnd:
    #                 self.socket.sendto(self.SndBuffer[i][1],
    #                                    self.clientAddress)
    #                 self.TimeStart = time.time()
    #                 self.SndBuffer[i][2] = True
    #             elif self.SndBuffer[i][2] == False:
    #                 break
    #         self.lock.release()
    #         if self.finished:
    #             break


class ServerSocket(object):
    def __init__(self, serverPort):
        self.serverPort = serverPort
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.connections = {}  # {clientAddress: LFTPServer}
        # self.lock = threading.Lock()
        self.pool = [
            threading.Thread(target=f)
            for f in [self.requestConnection, self.castConnection]
        ]

    def start(self):
        self.socket.bind('', self.serverPort)
        for t in self.pool:
            t.start()
        logger.info('The server is listening at {0}'.format(self.serverPort))

    def requestConnection(self):
        while True:
            segment, clientAddress = self.socket.recvfrom(1024)
            # lock.acquire()
            if clientAddress not in self.connections:
                logger.info('Accept connection from {0}'.format(clientAddress))
                self.connections[clientAddress] = LFTPServer(clientAddress)
            self.connections[clientAddress].rcvSegment(segment)
            # lock.release()
    def castConnection(self):
        while True:
            # lock.acquire()
            for c in list(self.connections.items()):
                if c[1].finished:
                    logger.info('Disconnect {0}'.format(c[0]))
                    del (self.connections[c[0]])
            # lock.release()


if __name__ == "__main__":
    serverSocket = ServerSocket(12000)
    serverSocket.start()