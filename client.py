#!/usr/bin/python3
#-*- coding: utf-8 -*-

DEST_IP = "127.0.0.1"
DEST_PORT = 16666
COMMAND = "lsend"
# filepath of the large file to upload to server
MY_LARGE_FILE = "ubuntu-18.04.1-desktop-amd64.iso"

import socket
import sys
import os
import UDPServer
import UDPClient

def clientMain():
	# Command check
	if COMMAND != "lsend" and COMMAND != "lget":
		print("Unknown command!")
		os._exit(0)
	
	# File check
	localFilePath = sys.path[0] + '/Test/Client/' + MY_LARGE_FILE
	if COMMAND == "lsend" and os.path.isfile(localFilePath) == False:
		print("File not exist :", localFilePath)
		os._exit(0)
	else:
		print("File :", localFilePath)
	
	# Path check, todo it's unnecessary
	if MY_LARGE_FILE.find('/') != -1:
		print("Documnet should be at current directory!")
		os._exit(0)

	# init UDP
	clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	
	# TCP handshake
	clientSocket.sendto(bytearray("HAND SHAKE 1", "utf-8"), (DEST_IP, DEST_PORT))
		# get server data and address from pkt
	serverData, serverAddr = clientSocket.recvfrom(1024)
	serverData = serverData.decode('utf-8')
		# resolve server data
	if serverData == "HAND SHAKE 2":
		print("Receive HAND SHAKE 2")
		clientSocket.sendto(bytearray("HAND SHAKE 3", "utf-8"), (DEST_IP, DEST_PORT))
	else:
		# exit
		print("Connect failed!")
		exit(0)
	print("Connect successfully!")

	# Get new port
	serverData, serverAddr = clientSocket.recvfrom(1024)
	serverPort = int(serverData.decode('utf-8'))
	print("Special port :", serverPort)

	# send request: lsend or lget
	clientSocket.sendto(bytearray(COMMAND, "utf-8"), (DEST_IP, serverPort))
	serverData, serverAddr = clientSocket.recvfrom(1024)
	serverData = serverData.decode('utf-8')
	print(serverData)
	# start transferring the large file
	clientSocket.sendto(bytearray(MY_LARGE_FILE, "utf-8"), (DEST_IP, serverPort))
	serverData, serverAddr = clientSocket.recvfrom(1024)
	serverData = serverData.decode('utf-8')
	print(serverData)
	if serverData == "File not exist":
		return

	# Transfer file
	if COMMAND == "lsend":
		print("Send", localFilePath, "to", serverAddr)
		UDPClient.sendFile(serverAddr, localFilePath)
	else:
		print("Receive", localFilePath, "to", serverAddr)
		UDPServer.getFile(serverPort, localFilePath)

if __name__ == "__main__":
	COMMAND = sys.argv[1]
	DEST_IP, DEST_PORT = sys.argv[2].split(':')
	DEST_PORT = int(DEST_PORT)
	MY_LARGE_FILE = sys.argv[3]
	clientMain()

	# send text test
	# sentData = bytearray("TEST", "utf-8")
	# clientSocket.sendto(sentData, (DEST_IP, DEST_PORT))
