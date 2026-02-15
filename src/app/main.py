#!/usr/bin/env python3

# Host application to capture serial data from the receiver M5Stick
# py5ライブラリを用いてProcessingの文法を使い、簡単にGUIインターフェースを作成する

import os
import sys
import math
#import serial
#import matplotlib.pyplot as plt  # --- 追加: グラフ用ライブラリ ---
from collections import deque    # --- 追加: データを保持するキュー ---
import edge                      # serialの代わり
import py5                       # pltの代わり。Processingに似た文法で簡単にGUIを作成できる



def nan2zero(x):
    # エラー値の処理
    if x is None or str(x) == 'nan':
        return 0.0
    else:
        return float(x)

def rss(xs):
    # root sum square
    return math.sqrt(sum((x * x for x in xs)))



# --- プログラム本体 ---

maxlen = 100  # グラフに表示するデータの個数
records = deque(maxlen=maxlen) # データを溜めるキュー、キューだから過去のデータが消えてく

def setup():
    # プログラムの最初に1度だけ呼ばれる
    py5.size(960, 480)  # ウィンドウサイズ
    py5.frame_rate(10)


def draw():
    # プログラム中繰り返し呼ばれる

    # データを読み込む
    tmp = edge.ask_records()
    count = len(tmp)                    # この描画フレームで読み込まれたデータ数
    records.extend(tmp)  # キューに追加

    # 描画
    py5.background(255) # 背景を白塗り
    py5.rect_mode(py5.CORNER)
    py5.stroke_weight(1)
    py5.stroke(0)
    py5.fill(255)
    py5.text_size(14)

    # 文字列表示
    py5.fill(0)
    py5.text_align(py5.LEFT, py5.TOP)
    py5.text('count: {}'.format(count), 480, 20)

    # グラフにプロット
    gx = 0         # グラフの左上座標
    gy = 0
    gw = 480       # グラフのサイズ
    gh = 480
    lw = 60        # 罫線の幅
    lh = 45
    uw = 400       # 太い罫線の幅
    uh = 180
    ox = 444       # 原点の相対位置
    oy = 240
    fs = 12        # フォントサイズ
    py5.stroke(0)
    py5.fill(246)
    py5.rect(gx, gy, gw, gh)
    py5.stroke(200)
    for i in range(- (ox // lw), ((gw - ox) // lw) + 1):
        py5.line(gx + ox + lw * i, gy, gx + ox + lw * i, gy + gh)
    for i in range(- (oy // lh), ((gh - oy) // lh) + 1):
        py5.line(gx, gy + oy + lh * i, gx + gw, gy + oy + lh * i)
    py5.stroke(55, 55, 177)
    if 0 <= ox - uw < gw:
        py5.line(gx + ox - uw, gy, gx + ox - uw, gy + gh)
    if 0 <= ox + uw < gw:
        py5.line(gx + ox + uw, gy, gx + ox + uw, gy + gh)
    if 0 <= oy - uh < gw:
        py5.line(gx, gy + oy - uh, gx + gw, gy + oy - uh)
    if 0 <= oy + uh < gh:
        py5.line(gx, gy + oy + uh, gx + gw, gy + oy + uh)
    py5.stroke(8)
    if 0 <= ox < gw:
        py5.line(gx + ox, gy, gx + ox, gy + gh)
    if 0 <= oy < gh:
        py5.line(gx, gy + oy, gx + gw, gy + oy)
    if len(records) != 0:
        q = records[-1]
        xs = [float(r.t - q.t) * uw / 1000.0 for r in records]
        yss = [
                (0, 'tilt', '/', (20, 20, 123),
                    [nan2zero(r.tilt) * uh / math.pi for r in records],
                    '{:d} deg'.format(int(nan2zero(records[-1].tilt) * 180 / math.pi)) ),
                (1, 'sensor accel', 'a', (199, 99, 0),
                    [nan2zero(rss(r.a)) * uh / 1.0 for r in records],
                    '{:.2f} m/s'.format(nan2zero(rss(records[-1].a))) ),
                (2, 'sensor gyro', 'w', (99, 33, 0),
                    [nan2zero(rss(r.w)) * uh / 30.0 for r in records],
                    '{:d} deg/s'.format(int(nan2zero(rss(records[-1].w)) * 180 / math.pi)) ),
                (3, 'jumping', '1', (0, 200, 0),
                    [lh if r.jumping else 0.0 for r in records],
                    'air' if records[-1].jump else 'ground' ),
                ]
        for idx, nam, ico, col, ys, val in reversed(yss):
            py5.stroke(*col)
            py5.fill(*col)
            py5.text_size(fs)
            py5.text_align(py5.LEFT, py5.CENTER)
            py5.text('{:1s} {}'.format(ico, val), gx + ox + xs[-1] + 2, gy + oy - ys[-1])
            py5.text_align(py5.LEFT, py5.TOP)
            py5.text('{:1s}: {}'.format(ico, nam), gx + 2, gy + fs * idx + 2)
            for i in range(len(xs) - 1):
                py5.line(gx + ox + xs[i], gy + oy - ys[i], gx + ox + xs[i+1], gy + oy - ys[i+1])

    # カーソル描画
    py5.stroke(255, 0, 0)
    py5.fill(255)
    py5.ellipse(py5.mouse_x, py5.mouse_y, 4, 4)




if __name__ == '__main__':

    if len(sys.argv) != 2:
        print('usage: {} PORT'.format(sys.argv[0]), file=sys.stderr)
        exit(254)

    port = sys.argv[1]
    baudrate = 115200

    rc = edge.init(port, baudrate)
    if rc != 0:
        exit(rc)
    py5.run_sketch()
