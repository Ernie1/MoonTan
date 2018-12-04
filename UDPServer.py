#!/usr/bin/python3

# Programming UDP with the terminology and idea of TCP
# Suppose the size of file is less than 4294967296 bytes
# Suppose file exists and filename is unique
import socket
import logging
import json
# import threading
import time
import os
import sys

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
	def __init__(self, clientAddress, filename, MSS):
		self.finished = False
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.clientAddress = clientAddress
		# ZYD update here for encapsulation
		self.filename = filename
		self.MSS = MSS
		# Suppose capacity of self.RcvBuffer is 65536 bytes, roughly floor( 65536 / self.MSS ) segments
		self.RcvBufferCapacity = int(65536 / self.MSS)
		# self.rwnd doesn't contains the length of segment header for convenient
		self.rwnd = 0
		self.RcvBuffer = []  # [(SeqNum, Data, sf)]
		self.first = True
		self.fileSize = 0
		self.progress = 1
		self.count = 0
		self.lastTime = 0

	def rcvSegment(self, segment):
		seqNum, _, _, sf, _ = fromHeader(segment)
		data = segment[12:]

		# ZYD : add a tmp var
		finishFlag = False
		# SYN
		if sf == 1:
			info = json.loads(data.decode())
			# ZYD : update it for encapsulation
			# self.file = open(info['filename'], 'wb')
			self.file = open(self.filename, 'wb')
			logger.info('Start to receive {0} from {1}'.format(
				info['filename'], self.clientAddress))
			self.NextSeqNum = seqNum + len(data)
		elif len(self.RcvBuffer) < self.RcvBufferCapacity and seqNum >= self.NextSeqNum:
			if self.first == True:
				self.fileSize = json.loads(data.decode())
				self.first = False
				if self.fileSize > 1073741824:
					logger.info("The size of file to be received is {:.3} GB".format(self.fileSize/1073741824))
				elif self.fileSize > 1048576:
					logger.info("The size of file to be received is {:.3} MB".format(self.fileSize/1048576))
				else:
					logger.info("The size of file to be received is {:.3} KB".format(self.fileSize/1024))
				self.NextSeqNum = seqNum + len(data)
				self.lastTime = time.time()
			else:
				# Show speed
				progress = self.progress
				tempFileName = self.filename.split('/')[-1]
				while self.count * self.MSS/ self.fileSize  >= self.progress * 0.05:
					self.progress += 1
				if progress < self.progress:
					logger.info('Received {0}%'.format((self.progress - 1) * 5))
					speed = self.count * self.MSS/(time.time() - self.lastTime)
					if speed > 1073741824:
						logger.info("Speed: {:.4} GB/s".format(speed/1073741824))
					elif speed > 1048576:
						logger.info("Speed: {:.4} MB/s".format(speed/1048576))
					else:
						logger.info("Speed: {:.4} KB/s".format(speed/1024))
				# Cast out from self.SndBuffer
				# while len(self.SndBuffer) and self.SndBuffer[0][0] < self.NextSeqNum:
				# 	# ZYD : get updateTimeoutInterval
				# 	self.updateTimeoutInterval(self.SndBuffer[0][3])
				# 	s = self.SndBuffer.pop(0)
				# 	# Determine whether last cast out is FIN
				# 	if len(self.SndBuffer) == 0 and self.fromHeader(s[1])[3] == 2:
				# 		self.running = False
				# 		self.socket.close()
				# 		logger.info('Finished')
				# finish showing progress
				i = 0
				while i < len(self.RcvBuffer) and self.RcvBuffer[i][0] < seqNum:
					i += 1
				# Determine whether duplicate
				if len(self.RcvBuffer) == 0 or i == len(self.RcvBuffer) or (self.RcvBuffer[i][0] != seqNum):
					self.RcvBuffer.insert(i, (seqNum, data, sf))
					# Cast out from self.RcvBuffer
					i = 0
					while i < len(self.RcvBuffer) and self.NextSeqNum == self.RcvBuffer[i][0]:
						self.NextSeqNum += len(self.RcvBuffer[i][1])
						# FIN
						if self.RcvBuffer[i][2] == 2:
							self.file.close()
							logger.info(
								'File received'.
								format(self.clientAddress))
							# ZYD : update here for encapsulation
							# self.asyncCloseConnection()
							finishFlag = True
						else:
							self.file.write(self.RcvBuffer[i][1])
							self.count+=1;
						i += 1
					self.RcvBuffer = self.RcvBuffer[i:]
					# ZYD : FIX An IMPORTANT BUG 2
					if len(self.RcvBuffer) == self.RcvBufferCapacity:
						self.RcvBuffer.pop(0)
		# ACK
		self.socket.sendto(
			toHeader(
				ackNum=self.NextSeqNum,
				ack=1,
				rwnd=(self.RcvBufferCapacity - len(self.RcvBuffer)) *
				self.MSS), self.clientAddress)
		return finishFlag

	def asyncCloseConnection(self):
		def closeConnection():
			time.sleep(30)
			self.socket.close()
			logger.info('Close connection to {0}'.format(self.clientAddress))
			self.finished = True

		threading.Thread(target=closeConnection).start()


class ServerSocket(object):
	def __init__(self, serverPort, MSS):
		self.serverPort = serverPort
		self.MSS = MSS
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.connections = {}  # {clientAddress: LFTPServer}

	def start(self, filename):
		self.socket.bind(('', self.serverPort))
		logger.info('The server is listening at {0}'.format(self.serverPort))
		# ZYD update here for encapsulation
		# threading.Thread(target=self.listen).start()
		self.listen(filename)

	def listen(self, filename):
		while True:
			segment, clientAddress = self.socket.recvfrom(self.MSS + 12)
			# logger.info("receive from client")
			# Cast out from self.connections
			for c in list(self.connections.items()):
				if c[1].finished:
					del (self.connections[c[0]])
			if clientAddress not in self.connections:
				# ZYD update here for encapsulation
				logger.info('Accept connection from {0}'.format(clientAddress))
				self.connections[clientAddress] = LFTPServer(
					clientAddress, filename, self.MSS)
			if self.connections[clientAddress].rcvSegment(segment):
				return


if __name__ == "__main__":
	server = ServerSocket(12000, 5360)
	server.start()

def getFile(PORT, filename):
	server = ServerSocket(PORT, 5360)
	server.start(filename)
