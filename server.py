#!/usr/bin/python3
#-*- coding: utf-8 -*-

import socket
import _thread
import os
import sys
import UDPServer
import UDPClient
import logging

# Initialize logger
logging.basicConfig(
	format=
	'%(asctime)s,%(msecs)03d - %(levelname)s - %(funcName)s - %(message)s',
	datefmt='%Y-%m-%d %H:%M:%S',
	level=logging.NOTSET)
logger = logging.getLogger()

ROOT_DIR = sys.path[0] + "/Test/Server/"
LISTEN_PORT = 16666

# thread to serve each client
def userConnection(clientAddr, serverPort):
	# Establish new port
	serverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	serverSocket.bind(('127.0.0.1', serverPort))
	s= " "
	logger.info("Start a new thread for : " + str(clientAddr) + " at port " + str(serverPort))

	# Send new port num
	serverSocket.sendto(bytearray(str(serverPort), "utf-8"), clientAddr)

	# Get command
	clientCommand, clientAddr = serverSocket.recvfrom(1024)
	clientCommand = clientCommand.decode('utf-8')
	logger.info("Received client command is " + clientCommand)
	serverSocket.sendto(bytearray("Got command", "utf-8"), clientAddr)

	# Get file name
	clientFileName, clientAddr = serverSocket.recvfrom(1024)
	clientFileName = clientFileName.decode('utf-8')
	print("File name :", clientFileName)

	# Check file exist when the client wants to get
	clientFileName = ROOT_DIR + clientFileName
	# when receiving lget and the file does not exist in server
	if clientCommand == "lget" and os.path.isfile(clientFileName) == False:
		print("File not exist :", clientFileName)
		serverSocket.sendto(bytearray("File not exist", "utf-8"), clientAddr)
		return
	# the file exists in server
	else:
		print("Check file exist :", clientFileName)
		serverSocket.sendto(bytearray("Got file name", "utf-8"), clientAddr)

	# Transfer file
	# client sends, server gets
	if clientCommand == "lsend":
		serverSocket.close()
		print("Receive",clientFileName, "from", clientAddr)
		UDPServer.getFile(serverPort, clientFileName)
	# client gets, server sends
	else:
		print("Send",clientFileName, "to", (clientAddr[0],serverPort))
		UDPClient.sendFile((clientAddr[0],serverPort), clientFileName)


def serverMain():
	print("The root directory is " + ROOT_DIR)
	serverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	serverSocket.bind(('127.0.0.1', 16666))
	print("UDP listening on", LISTEN_PORT)

	# waiting for connecting
	rejudge = False
	userCount = 0
	while True:
		if rejudge == False:
			clientData, clientAddr = serverSocket.recvfrom(1024) # buffer size
			clientData = clientData.decode('utf-8')
		# TCP head shake
		if clientData == "HAND SHAKE 1":
			print("Receive HAND SHAKE 1")
			serverSocket.sendto(bytearray("HAND SHAKE 2", "utf-8"), clientAddr)
			clientData, clientAddr = serverSocket.recvfrom(1024)
			clientData = clientData.decode('utf-8')
			if clientData == "HAND SHAKE 3":
				print(clientAddr, "has established a connect")
				rejudge = False
				userCount += 1
				print("User num =", userCount)
				_thread.start_new_thread(userConnection, (clientAddr, LISTEN_PORT+userCount))
			else:
				print(clientAddr, "established a connect failed")
				rejudge = True
		else:
			print("Error establish request:", clientData)
			rejudge = False


if __name__ == "__main__":
	serverMain()
		


	# receive text test
	# clientData, clientAddr = serverSocket.recvfrom(1024)
	# print('Received from %s:%s.' % clientAddr)
	# clientData = clientData.decode('utf-8')
	# print("\t"+str(clientData))
		

	# Read data test
	# filePointer = open(ROOT_DIR+"Background.pdf", "rb")
	# fileData = bytearray(filePointer.read())
	# filePointer.close()
	

	# Write test
	# filePointer = open(ROOT_DIR+"Background2.pdf", "wb")
	# filePointer.write(fileDataArray)
	# filePointer.close()
