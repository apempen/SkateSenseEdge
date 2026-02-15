#!/usr/bin/env python3

# Host application to capture serial data from the receiver M5Stick
# p5ライブラリを用いてProcessingの文法を使い、簡単にGUIインターフェースを作成する

import os
import sys
#import serial
#import matplotlib.pyplot as plt  # --- 追加: グラフ用ライブラリ ---
from collections import deque    # --- 追加: データを保持するキュー ---
import edge                      # serialの代わり
import p5                        # pltの代わり。Processingに似た文法で簡単にGUIを作成できる


maxlen = 100  # グラフに表示するデータの個数
y_data = deque([0.0]*maxlen, maxlen=maxlen) # データを溜めるキュー、キューだから過去のデータが消えてく
coord = lambda u: (u[0] * 2 + 200, - u[1] * 14 + 100)

def setup():
    # プログラムの最初に1度だけ呼ばれる
    p5.size(640, 480)  # ウィンドウサイズ


def draw():
    # プログラム中繰り返し呼ばれる

    # データを読み込む
    for record in edge.ask_records():
        val = record.tilt
        if str(val) == 'nan': val = 0.0 # エラー値の処理
        y_data.append(val)

    # グラフ描画
    p5.background(255)
    p5.stroke(128)
    p5.line((0, 50), (200, 50))
    p5.line((0, 150), (200, 150))
    p5.stroke(0)
    p5.line((0, 100), (200, 100))
    p5.line((100, 0), (100, 200))
    p5.stroke(200, 200, 0)
    for i in range(len(y_data) - 1):
        p0 = coord((-i, y_data[-i]))
        p1 = coord((-i-1, y_data[-i-1]))
        p5.line(p0, p1)

    # カーソル描画
    p5.stroke(255, 0, 0)
    p5.fill(255)
    p5.ellipse(mouse_x, mouse_y, 4, 4)



def main(port, baudrate):
    rc = edge.init(port, baudrate)
    if rc != 0:
        return rc
    p5.run()
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
