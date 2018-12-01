# Programming UDP with the terminology and idea of TCP
# Suppose the size of file is less than 4294967296 bytes
# Suppose file exists and filename is unique
import socket
import logging
import json
import threading
import time

# Initialize logger
logging.basicConfig(
    format=
    '%(asctime)s,%(msecs)03d - %(levelname)s - %(funcName)s - %(message)s',
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
    def __init__(self, clientAddress):
        self.finished = False
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.clientAddress = clientAddress
        # self.rwnd doesn't contains the length of segment header for convenient
        self.rwnd = 0
        self.RcvBuffer = []  # [(SeqNum, Data, sf)]

    def rcvSegment(self, segment):
        seqNum, _, _, sf, _ = fromHeader(segment)
        data = segment[12:]
        # SYN
        if sf == 1:
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
            if len(self.RcvBuffer) == 0 or i == len(
                    self.RcvBuffer) or (self.RcvBuffer[i][0] != seqNum
                                        and seqNum >= self.NextSeqNum):
                self.RcvBuffer.insert(i, (seqNum, data, sf))
                # Cast out from self.RcvBuffer
                i = 0
                while i < len(self.RcvBuffer
                              ) and self.NextSeqNum == self.RcvBuffer[i][0]:
                    self.NextSeqNum += len(self.RcvBuffer[i][1])
                    # FIN
                    if self.RcvBuffer[i][2] == 2:
                        self.file.close()
                        logger.info('Finished for {0}, wait to close connection'.format(self.clientAddress))
                        self.asyncCloseConnection()
                    else:
                        self.file.write(self.RcvBuffer[i][1])
                    i += 1
                self.RcvBuffer = self.RcvBuffer[i:]
        # ACK
        # Suppose capacity of self.RcvBuffer is 65536 bytes, 65536 / 576 roughly 113 segments
        self.socket.sendto(
            toHeader(
                ackNum=self.NextSeqNum,
                ack=1,
                rwnd=(113 - len(self.RcvBuffer)) * 536), self.clientAddress)
    
    def asyncCloseConnection(self):
        def closeConnection():
            time.sleep(30)
            self.finished = True
            self.socket.close()
            logger.info('Closed')
        threading.Thread(target=closeConnection).start()

class ServerSocket(object):
    def __init__(self, serverPort):
        self.serverPort = serverPort
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.connections = {}  # {clientAddress: LFTPServer}
        self.pool = [
            threading.Thread(target=f)
            for f in [self.requestConnection, self.castConnection]
        ]

    def start(self):
        self.socket.bind(('', self.serverPort))
        for t in self.pool:
            t.start()
        logger.info('The server is listening at {0}'.format(self.serverPort))

    def requestConnection(self):
        while True:
            segment, clientAddress = self.socket.recvfrom(1024)
            if clientAddress not in self.connections:
                logger.info('Accept connection from {0}'.format(clientAddress))
                self.connections[clientAddress] = LFTPServer(clientAddress)
            self.connections[clientAddress].rcvSegment(segment)

    def castConnection(self):
        while True:
            for c in list(self.connections.items()):
                if c[1].finished:
                    logger.info('Disconnect {0}'.format(c[0]))
                    del (self.connections[c[0]])


if __name__ == "__main__":
    server = ServerSocket(12000)
    server.start()