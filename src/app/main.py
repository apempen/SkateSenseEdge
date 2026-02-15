#!/usr/bin/env python3

# Host application to capture serial data from the receiver M5Stick

import os
import sys
#import serial
import matplotlib.pyplot as plt  # --- 追加: グラフ用ライブラリ ---
from collections import deque    # --- 追加: データを保持するキュー ---
import edge                      # serialの代わり


def main(port, baudrate):
    edge.init(port, baudrate)

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
            # データを読み込む
            for record in edge.ask_records():
                i += 1
                val = record.a[0]
                if str(val) == 'nan': val = 0.0 # エラー値の処理
                y_data.append(val)

            # 0.2秒に1回表示
            lines.set_ydata(y_data) # データの更新
            plt.pause(0.2) #これが、いつものplt.show()を表す。(時間)

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
