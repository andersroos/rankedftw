#!/usr/bin/env python3

import sys
import socket


def send(host, port, message):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(message.encode('utf-8'), (host, port))
    
    response = sock.recvfrom(65535)
    print(response[0].decode('utf-8'))
    
if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: " + sys.argv[0] + " <host> <port> <message>")
        exit(1)

    send(sys.argv[1], int(sys.argv[2]), sys.argv[3])
