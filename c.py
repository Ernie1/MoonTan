import socket
clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
clientSocket.sendto(b'hello', ('172.18.196.136',12000))
