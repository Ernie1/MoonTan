import socket
serverPort = 12000
serverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
serverSocket.bind(('', serverPort))
print('The server is ready to receive')
while True:
    message, clientAddress = serverSocket.recvfrom(2048)
    print(messagecode(), clientAddress)
    modifiedMessage = message.decode().upper()
    serverSocket.sendto(modifiedMessage.encode(), clientAddress)

connectionSocket

def fromHeader(self, segment):
        return int.from_bytes(
            segment[:4], byteorder="little"), int.from_bytes(
                segment[4:8], byteorder="little"), int.from_bytes(
                    segment[8:9], byteorder="little"), int.from_bytes(
                        segment[9:10], byteorder="little"), int.from_bytes(
                            segment[10:12], byteorder="little")
