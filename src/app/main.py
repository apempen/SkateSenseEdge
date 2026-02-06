#!/usr/bin/env python3

# Host application to capture serial data from the receiver M5Stick

import os
import sys
import time
import serial
import serial.tools.list_ports


def open_serial(port, baudrate, skip_some=True):
    # open a serial port to communicate via USB
    try:
        ser = serial.Serial(port=port, baudrate=baudrate)
    except serial.SerialException as e:
        print('SerialException:', e, file=sys.stderr)
        return 8
    if not ser.isOpen():
        ser.open()
    if skip_some:
        for _ in range(3):
            ser.readline()  # flush buffer
    return ser


def parse_line(line):
    # split line (str) to data (list of float)
    default = [float('nan')] * 6
    xx = [x.strip() for x in line.split(b',')]
    try:
        xx = [float(x) for x in xx]
    except ValueError:
        xx = default
    if len(xx) < 6:
        xx += [float('nan')] * (6 - len(xx))
    elif len(xx) > 6:
        xx = xx[:6]
    return xx


def get_time_ms():
    # what time is it now? (milliseconds, integer)
    return int(time.time() * 1000)


def main(port, baudrate):

    # open serial
    print('# try to open serial port {} (baudrate={})'.format(port, baudrate))
    ser = open_serial(port, baudrate)
    if ser is not None:
        print('#   succeeded!')
    else:
        print('#   failed...')
        return 1

    # get epoch time
    epoch = get_time_ms()

    # display
    print('# please hit Ctrl+C to exit')
    try:
        i = 0
        while True:
            # read one line
            line = ser.readline()
            data = parse_line(line)
            print('data #{:06d},{:10d}ms: acc=[{:7.3f},{:7.3f},{:7.3f}], gyro=[{:7.3f},{:7.3f},{:7.3f}]'.format(
                i, get_time_ms() - epoch,
                data[0], data[1], data[2], data[3], data[4], data[5] ))
    except KeyboardInterrupt:
        print('# bye')

    return 0


if __name__ == '__main__':

    if len(sys.argv) != 2:
        print('usage: {} PORT'.format(sys.argv[0]), file=sys.stderr)
        exit(254)

    port = sys.argv[1]
    baudrate = 115200

    exit(main(
        port=port, baudrate=baudrate,
        ) or 0)

