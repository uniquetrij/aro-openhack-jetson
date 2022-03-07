import os, pty, serial
import random
from threading import Thread
from time import sleep

master, slave = pty.openpty()
m_name = os.ttyname(master)
s_name = os.ttyname(slave)
def start_reading():
    # ser = serial.Serial(m_name)
    while True:
        # print(ser.read())
        print(os.read(master, 1000))


def serial_connect(serial_port):
    ser = serial.Serial(s_name)
    while True:
        ser.write((str(random.uniform(97, 98))+';').encode('utf-8'))
        sleep(1)


def serial_read(param):
    return master


Thread(target=start_reading).start()
Thread(target=serial_connect, args=('',)).start()