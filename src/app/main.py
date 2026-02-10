#!/usr/bin/env python3

# Host application to capture serial data from the receiver M5Stick

import os
import sys
import time
import serial
import serial.tools.list_ports
import matplotlib.pyplot as plt  # --- 追加: グラフ用ライブラリ ---
from collections import deque    # --- 追加: データを保持するキュー ---

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

    #グラフの初期設定
    plt.ion() #動的なグラフの作成らしい
    fig, ax = plt.subplots() #グラフの設定。figがウィンドウ、axが点
    maxlen = 100  # グラフに表示するデータの個数
    y_data = deque([0.0]*maxlen, maxlen=maxlen) # データを溜めるキュー、キューだから過去のデータが消えてく
    lines, = ax.plot(range(maxlen), y_data)     # プロットオブジェクト作成
    ax.set_ylim(-1.5, 1.5) #データの振れ幅が今回は+-1.0
    
    # display
    print('# please hit Ctrl+C to exit')
    try:
        i = 0
        while True:
            # read one line
            line = ser.readline()
            data = parse_line(line)
            print('data #{:06d},{:10d}ms: acc=[{:7.3f}]'.format(
                i, get_time_ms() - epoch,
                data[0])) #念のためdata[0]だけ表示した。消してもいい。

            val = data[0]
            if str(val) == 'nan': val = 0.0 # エラー値の処理
            y_data.append(val)

            # 5回に1回更新
            if i % 5 == 0:
                lines.set_ydata(y_data) # データの更新
                
                plt.pause(0.001) #これが、いつものplt.show()を表す。(時間)
            
            i += 1 #これ抜けてた。ずっとi=0のまんまだった
            
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