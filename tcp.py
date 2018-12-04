import socket
import os
import _thread
import server
import client


def send(filePath, addr, socket):
    print("TCP: Send", filePath, "to", addr)
    # filePointer = open(filePath, "rb")

    # Send file Len
    fileLen = os.path.getsize(filePath)
    socket.sendto(bytearray(str(fileLen), "utf-8"), addr)

    # Receive rwind
    fileLen, addr = socket.recvfrom(1024)
    fileLen = int(fileLen.decode('utf-8'))

    # Read file
    # fileData = bytearray(filePointer.read())


def receive(filePath, addr, socket):
    print("TCP: Receive", filePath, "from", addr)
    # filePointer = open(filePath, "wb")

    # Receive file len
    fileLen, addr = socket.recvfrom(1024)
    fileLen = int(fileLen.decode('utf-8'))
    print("File len:", fileLen, "bytes")

    # Send rwind
    rwind = 1024000
    socket.sendto(bytearray(str(rwind), "utf-8"), addr)


#debug
if __name__ == "__main__":
    _thread.start_new_thread(server.serverMain)
    _thread.start_new_thread(client.clientMain)
    pass