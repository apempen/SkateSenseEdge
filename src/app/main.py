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
import numpy as np
from graph import GraphDrawer, SphereDrawer  # グラフ表示用のスクリプト




def nan2zero(x):
    # エラー値の処理
    if x is None:
        return 0.0
    elif isinstance(x, float):
        if str(x) == 'nan':
            return 0.0
        else:
            return x
    elif isinstance(x, int):
        return float(x)
    else:
        try:
            return list(map(nan2zero, x))
        except TypeError:
            return 0.0

def rss(xs):
    # root sum square
    return math.sqrt(sum((x * x for x in xs)))

def vmul(xs, a):
    # リストの各要素に a を掛ける
    return [x * a for x in xs]



# --- プログラム本体 ---

maxlen = 100  # グラフに表示するデータの個数
records = deque(maxlen=maxlen) # データを溜めるキュー、キューだから過去のデータが消えてく
lastmouse = False
pivotx = 0
pivoty = 0

graph = None
sphere = None

def setup():
    global graph, sphere
    # プログラムの最初に1度だけ呼ばれる
    py5.size(960, 480)  # ウィンドウサイズ、P3Dとすることで3次元描画が可能
    py5.frame_rate(10)
    graph = GraphDrawer(400, 400)
    sphere = SphereDrawer(400, 400)


def draw():
    global lastmouse, pivotx, pivoty
    # プログラム中繰り返し呼ばれる

    # データを読み込む
    tmp = edge.ask_records()
    count = len(tmp)                    # この描画フレームで読み込まれたデータ数
    records.extend(tmp)  # キューに追加

    # TODO: 以下の描画用コードは仮置きなので、後々見やすいように書き換える必要があります

    # 球の回転
    #   左クリックしながらカーソルを動かすと球を回転できる
    rx = ry = 0
    if py5.is_mouse_pressed:
        if lastmouse is False:
            pivotx = py5.mouse_x
            pivoty = py5.mouse_y
        rx = py5.mouse_x - pivotx
        ry = py5.mouse_y - pivoty
        lastmouse = True
    else:
        if lastmouse is True:
            sphere.scroll(py5.mouse_x - pivotx, py5.mouse_y - pivoty)
        rx = 0
        ry = 0
        lastmouse = False

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
    if len(records) != 0:
        py5.text(repr(records[-1]), 10, 410, py5.width - 20, py5.height - 420)

    # グラフにプロット
    if len(records) != 0:
        rec0 = records[-1]
        xs = [float(rec.t - rec0.t) / 1000.0 for rec in records]
        graph.set_xs(xs, fn_value  = lambda x: x * 2 + 1.0 )
        graph.set_ys([nan2zero(rec.tilt) for rec in records],
                'tilt', icon='/', color=(20,20,223),
                fn_value  = lambda y: y / math.pi,
                fn_pretty = lambda y: '{:d} deg'.format(int(y * 180 / math.pi)) )
        graph.set_ys([nan2zero(rss(rec.a)) for rec in records],
                'sensor accel', icon='a', color=(255,99,0),
                fn_value  = lambda y: y * 0.4 - 1.0,
                fn_pretty = lambda y: '{:.2f} G'.format(y) )
        graph.set_ys([nan2zero(rss(rec.w)) for rec in records],
                'sensor gyro', icon='g', color=(155,33,0),
                fn_value  = lambda y: y * math.pi / 180 * 0.2 - 1.0,
                fn_pretty = lambda y: '{:d} deg/s'.format(int(y)) )
        graph.set_ys([rec.jumping for rec in records],
                'jumping', icon='J', color=(0,200,0),
                fn_value  = lambda y: -0.01 + 0.02 * int(y),
                fn_pretty = lambda y: 'air' if y else 'grounded' )
        sphere.set_vector(nan2zero(rec0.a),
                'sensor accel', icon='a', color=(255,99,0),
                fn_value  = lambda y: vmul(y, 1.0),
                fn_pretty = lambda y: '{:.2f} G'.format(rss(y)) )
        sphere.set_vector(nan2zero(rec0.w),
                'sensor gyro', icon='w', color=(155,33,0),
                fn_value  = lambda y: vmul(y, math.pi / 180 * 0.4),
                fn_pretty = lambda y: '{:d} deg/s'.format(int(rss(y))) )
    graph.plot(40, 0)
    sphere.plot(480, 0, rx, ry)

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
