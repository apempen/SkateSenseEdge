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
rot1 = 0.0     # 級の回転角
rot2 = 0.9

def setup():
    # プログラムの最初に1度だけ呼ばれる
    py5.size(960, 480, py5.P3D)  # ウィンドウサイズ、P3Dとすることで3次元描画が可能
    py5.frame_rate(10)


def draw():
    global rot1, rot2
    # プログラム中繰り返し呼ばれる

    # データを読み込む
    tmp = edge.ask_records()
    count = len(tmp)                    # この描画フレームで読み込まれたデータ数
    records.extend(tmp)  # キューに追加

    # TODO: 以下の描画用コードは仮置きなので、後々見やすいように書き換える必要があります

    # 球の回転
    if py5.is_mouse_pressed:
        rot1 += (py5.mouse_x - py5.pmouse_x) * math.pi / 2 / 120
        rot2 += (py5.mouse_y - py5.pmouse_y) * math.pi / 2 / 120

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
    gx = 0         # グラフの左上座標
    gy = 0
    gw = 480       # グラフのサイズ
    gh = 400
    lw = 60        # 罫線の幅
    lh = 45
    uw = 400       # 太い罫線の幅
    uh = 180
    ox = 444       # 原点の相対位置
    oy = 200
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
                # ここに書き足すことでプロットするデータを追加できます
                # 凡例: (
                #   通し番号,
                #   名前,
                #   識別用の記号,
                #   グラフの色（RGB）,
                #   プロットするy座標の配列（値域が [-uh,uh] 程度になるようにスケーリングする）,
                #   現在の値（文字列で単位付き） )
                (0, 'tilt', '/', (20, 20, 123),
                    [nan2zero(r.tilt) * uh / math.pi for r in records],
                    '{:d} deg'.format(int(nan2zero(q.tilt) * 180 / math.pi)) ),
                (1, 'sensor accel', 'a', (199, 99, 0),
                    [nan2zero(rss(r.a)) * uh / 1.0 for r in records],
                    '{:.2f} m/s'.format(nan2zero(rss(q.a))) ),
                (2, 'sensor gyro', 'w', (99, 33, 0),
                    [nan2zero(rss(r.w)) * uh / 30.0 for r in records],
                    '{:d} deg/s'.format(int(nan2zero(rss(q.w)) * 180 / math.pi)) ),
                (3, 'jumping', '1', (0, 200, 0),
                    [lh if r.jumping else 0.0 for r in records],
                    'air' if q.jump else 'ground' ),
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

    # スフィア描画
    gx = 480          # 画像の左上
    gy = 0
    ox = 240          # 球体の中心
    oy = 180
    oz = 0
    rr = 100          # 球体の半径
    nn = 16           # テッセレーション
    rx = 1.4          # 傾き
    ry = 0.0
    rz = 0.1
    fs = 12           # フォントサイズ
    py5.push_matrix()
    py5.stroke(200)
    py5.no_fill()
    py5.translate(gx + ox, gy + oy, 0 + oz)
    py5.rotate_x(rx)
    py5.rotate_y(ry + rot2)
    py5.rotate_z(rz + rot1)
    py5.circle(0, 0, rr * 2)
    py5.rotate_x(math.pi / 2)
    py5.circle(0, 0, rr * 2)
    py5.rotate_x(- math.pi / 2)
    py5.rotate_y(math.pi / 2)
    py5.circle(0, 0, rr * 2)
    py5.rotate_y(- math.pi / 2)
    py5.push_matrix()
    py5.translate(0, 0, rr / 2)
    py5.circle(0, 0, rr * math.sqrt(3))
    py5.translate(0, 0, rr * (math.sqrt(3) - 1) / 2)
    py5.circle(0, 0, rr)
    py5.pop_matrix()
    py5.push_matrix()
    py5.translate(0, 0, - rr / 2)
    py5.circle(0, 0, rr * math.sqrt(3))
    py5.translate(0, 0, - rr * (math.sqrt(3) - 1) / 2)
    py5.circle(0, 0, rr)
    py5.pop_matrix()
    py5.stroke(255, 0, 0)
    py5.line(0, 0, 0, rr * 1.5, 0, 0)
    py5.stroke(0, 255, 0)
    py5.line(0, 0, 0, 0, rr * 1.5, 0)
    py5.stroke(0, 0, 255)
    py5.line(0, 0, 0, 0, 0, rr * 1.5)
    if len(records) != 0:
        q = records[-1]
        arrows = [
                # ここに書き足すことでプロットするデータを追加できます
                # 凡例: (
                #   通し番号,
                #   名前,
                #   識別用の記号,
                #   グラフの色（RGB）,
                #   プロットする3次元ベクトル（ノルムが rr * 2 程度になるようにスケーリングする）,
                #   現在の値（文字列で単位付き） )
                (0, 'sensor accel', 'a', (199, 99, 0),
                    [x * rr / 1.0 for x in q.a],
                    '{:.2f} m/s'.format(nan2zero(rss(q.a))) ),
                (1, 'sensor gyro', 'w', (99, 33, 0),
                    [x * rr / 30.0 for x in q.w],
                    '{:d} deg'.format(int(nan2zero(rss(q.w)) * 180 / math.pi)) ),
                (2, 'down', '$', (55, 55, 177),
                    [x * rr / 1.0 for x in q.g],
                    '{:.2f} m/s'.format(nan2zero(rss(q.g))) ),
                ]
        for idx, nam, ico, col, p, val in reversed(arrows):
            py5.stroke_weight(2)
            py5.stroke(*col)
            py5.fill(*col)
            py5.text_size(fs)
            py5.text_align(py5.LEFT, py5.CENTER)
            py5.text('{:1s} {}'.format(ico, val), *p)
            py5.line(0, 0, 0, *p)
    py5.pop_matrix()

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
