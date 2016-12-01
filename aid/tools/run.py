#!/usr/bin/env python3
import sys
import subprocess

from signal import SIGINT, signal
from multiprocessing import Process
from time import sleep

cmds = sys.argv[1:]

if not cmds:
    exit("run args at once, kill all on int")


stop = False


def handler(sig, frame):
    global stop
    stop = True


def run_child(cmd):
    return subprocess.call(cmd, shell=True)


signal(SIGINT, handler)


children = []

for cmd in cmds:
    children.append(Process(target=run_child, args=[cmd]))

for c in children:
    c.start()

while not stop:
    sleep(0.1)

for c in children:
    c.terminate()
