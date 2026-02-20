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



def _pick_color(n):
    return (100, 200, 100)


class GraphDrawer:

    # 2次元グラフ描画処理
    #   draw関数内で、データ系列をset_data関数で指定した後plot関数で表示する

    def __init__(self, w, h, *, fontsize=12):
        self.__gw = w                # グラフの幅
        self.__gh = h
        self.__lw = int(w / 11)      # 罫線の幅
        self.__lh = int(h / 11)
        self.__uw = int(w * 5 / 11)  # 太い罫線の幅および値の単位
        self.__uh = int(h * 5 / 11)
        self.__ox = int(w / 2)       # 原点
        self.__oy = int(h / 2)
        self.__fs = fontsize         # フォントサイズ
        self.__xs = None             # x座標列
        self.__yss = []              # y座標列のリスト

    def set_xs(self, xs, *, fn_value=None, fn_pretty=None):
        if fn_value is None:
            values = [x * self.__uw for x in xs]
        else:
            values = [fn_value(x) * self.__uw for x in xs]
        self.__xs = values

    def set_ys(self, ys, name, *, icon=None, color=None, fn_value=None, fn_pretty=None):
        idx = len(self.__yss)
        if not isinstance(name, str):
            raise TypeError('name')
        if icon is None:
            icon = '*'
        elif isinstance(icon, str):
            pass
        else:
            raise TypeError('icon')
        if color is None:
            color = _pick_color(idx)
        elif isinstance(color, tuple) and len(color) <= 4 and all((isinstance(x, int) for x in color)):
            pass
        else:
            raise TypeError('color')
        if fn_value is None:
            values = [y * self.__uh for y in ys]
        else:
            values = [fn_value(y) * self.__uh for y in ys]
        if fn_pretty is None:
            current = ''
        elif len(ys) != 0:
            current = str(fn_pretty(ys[-1]))
        else:
            current = 'N/A'
        self.__yss.append(
                (idx, name, icon, color, values, current) )

    def reset(self):
        self.__xs = None
        self.__yss.clear()

    def plot(self, gx, gy):
        # 描画する
        py5.translate(gx, gy)
        self._plot_background()
        self._plot_lines()
        py5.translate(-gx, -gy)
        self.reset()

    def _plot_background(self):
        py5.stroke(0)
        py5.fill(246)
        py5.rect(0, 0, self.__gw, self.__gh)
        py5.stroke(200)
        for i in range(- (self.__ox // self.__lw), ((self.__gw - self.__ox) // self.__lw) + 1):
            py5.line(self.__ox + self.__lw * i, 0, self.__ox + self.__lw * i, self.__gh)
        for i in range(- (self.__oy // self.__lh), ((self.__gh - self.__oy) // self.__lh) + 1):
            py5.line(0, self.__oy + self.__lh * i, self.__gw, self.__oy + self.__lh * i)
        py5.stroke(55, 55, 177)
        if 0 <= self.__ox - self.__uw < self.__gw:
            py5.line(self.__ox - self.__uw, 0, self.__ox - self.__uw, self.__gh)
        if 0 <= self.__ox + self.__uw < self.__gw:
            py5.line(self.__ox + self.__uw, 0, self.__ox + self.__uw, self.__gh)
        if 0 <= self.__oy - self.__uh < self.__gw:
            py5.line(0, self.__oy - self.__uh, self.__gw, self.__oy - self.__uh)
        if 0 <= self.__oy + self.__uh < self.__gh:
            py5.line(0, self.__oy + self.__uh, self.__gw, self.__oy + self.__uh)
        py5.stroke(8)
        if 0 <= self.__ox < self.__gw:
            py5.line(self.__ox, 0, self.__ox, self.__gh)
        if 0 <= self.__oy < self.__gh:
            py5.line(0, self.__oy, self.__gw, self.__oy)

    def _plot_lines(self):
        xs = self.__xs
        if xs is None or len(xs) == 0:
            return
        for idx, nam, ico, col, ys, cur in reversed(self.__yss):
            if ys is None or len(ys) == 0:
                continue
            elif len(ys) != len(xs):
                n = min(len(xs), len(ys))
                xs = xs[:n]
                ys = ys[:n]
            py5.stroke(*col)
            py5.fill(*col)
            py5.text_size(self.__fs)
            py5.text_align(py5.LEFT, py5.CENTER)
            py5.text('{} {}'.format(ico, cur), self.__ox + xs[-1] + 2, self.__oy - ys[-1])
            py5.text_align(py5.LEFT, py5.TOP)
            py5.text('{}: {}'.format(ico, nam), 2, self.__fs * idx + 2)
            for i in range(len(xs) - 1):
                py5.line(self.__ox + xs[i], self.__oy - ys[i], self.__ox + xs[i+1], self.__oy - ys[i+1])


def _rot_x(th):
    c = np.cos(th)
    s = np.sin(th)
    return np.array([[ 1,  0,  0,  0],
                     [ 0,  c, -s,  0],
                     [ 0,  s,  c,  0],
                     [ 0,  0,  0,  1]], dtype=float)
def _rot_y(th):
    c = np.cos(th)
    s = np.sin(th)
    return np.array([[ c,  0,  s,  0],
                     [ 0,  1,  0,  0],
                     [-s,  0,  c,  0],
                     [ 0,  0,  0,  1]], dtype=float)
def _rot_z(th):
    c = np.cos(th)
    s = np.sin(th)
    return np.array([[ c, -s,  0,  0],
                     [ s,  c,  0,  0],
                     [ 0,  0,  1,  0],
                     [ 0,  0,  0,  1]], dtype=float)

def _trans(x, y, z):
    return np.array([[ 1,  0,  0,  x],
                     [ 0,  1,  0,  y],
                     [ 0,  0,  1,  z],
                     [ 0,  0,  0,  1]], dtype=float)

def _mkv(x, y, z):
    return np.array([[x], [y], [z], [1]], dtype=float)

_hr0 = 0
_hr1 = 1 / 2
_hr2 = np.sqrt(2) / 2
_hr3 = np.sqrt(3) / 2
_hr4 = 1
_hx0 = 0
_hx1 = math.pi / 6
_hx2 = math.pi / 4
_hx3 = math.pi / 3
_hx4 = math.pi / 2

class SphereDrawer:

    # ベクトルの向きと大きさを表示する

    def __init__(self, w, h, *, fontsize=12):
        self.__gw = w                # グラフの幅
        self.__gh = h
        self.__ox = w // 2           # 球の中心座標
        self.__oy = h // 2
        self.__oz = -min(w, h)
        self.__rr = min(w, h) // 4   # 球の半径
        self.__nn = 16               # テッセレーション
        self.__fs = fontsize         # フォントサイズ
        self.__vecs = []
        # 計算用ベクトル、行列
        self.__mat_r = _rot_x(0)
        self.__mat_r = _rot_x(-math.pi / 10) @ _rot_y(- math.pi / 4) @ _rot_x(math.pi / 2)


    def set_vector(self, vec, name, *, icon=None, color=None, fn_value=None, fn_pretty=None):
        idx = len(self.__vecs)
        if not isinstance(name, str):
            raise TypeError('name')
        if icon is None:
            icon = '*'
        elif isinstance(icon, str):
            pass
        else:
            raise TypeError('icon')
        if color is None:
            color = _pick_color(idx)
        elif isinstance(color, tuple) and len(color) <= 4 and all((isinstance(x, int) for x in color)):
            pass
        else:
            raise TypeError('color')
        if fn_value is None:
            value = vec
        else:
            value = fn_value(vec)
        if fn_pretty is None:
            current = ''
        elif len(vec) != 0:
            current = str(fn_pretty(vec))
        else:
            current = 'N/A'
        self.__vecs.append(
                (idx, name, icon, color, value, current) )

    def reset(self):
        self.__vecs.clear()

    def plot(self, gx, gy, rx=0, ry=0):
        # 描画
        tmp_mat_r = self.__mat_r
        if rx != 0 or ry != 0:
            self.scroll(rx, ry)
        py5.translate(gx, gy)
        self._plot_background()
        self._plot_lines()
        py5.translate(-gx, -gy)
        self.__mat_r = tmp_mat_r
        self.reset()

    def _scroll(self, dx, dy):
        th = math.atan2(dy, dx)
        ph = rss((dx, dy)) / self.__rr
        mat_pp = _rot_z(- th)
        mat_rr = _rot_y(ph)
        return mat_pp.T @ mat_rr @ mat_pp

    def scroll(self, dx, dy):
        self.__mat_r = self._scroll(dx, dy) @ self.__mat_r

    def _screen(self, xx):
        xx = self.__mat_r @ xx
        coef = - self.__rr / (self.__oz / self.__rr + xx[2,0])
        return coef * xx[0,0] + self.__ox, coef * xx[1,0] + self.__oy


    def _circle3d(self, ox, oy, oz, rr, rx, ry):
        oo = _mkv(ox, oy, oz)
        di = _rot_x(rx) @ _rot_y(ry)
        points = [self._screen(oo + di @ _rot_z(2 * math.pi * i / self.__nn) @ _mkv(rr, 0, 0)) for i in range(self.__nn)]
        points.append(points[0])
        for i in range(self.__nn):
            py5.line(points[i][0], points[i][1], points[i+1][0], points[i+1][1])
        aa = oo + di @ _mkv(rr, 0, 0)
        bb = self._screen(aa)

    def _line3d(self, x1, y1, z1, x2, y2, z2):
        p1 = self._screen(_mkv(x1, y1, z1))
        p2 = self._screen(_mkv(x2, y2, z2))
        py5.line(p1[0], p1[1], p2[0], p2[1])

    def _plot_background(self):
        py5.stroke(0)
        py5.fill(246)
        py5.rect(0, 0, self.__gw, self.__gh)
        py5.stroke(200)
        py5.no_fill()
        self._circle3d(0, 0, _hr0, _hr4, 0, 0)
        self._circle3d(0, 0, _hr1, _hr3, 0, 0)
        self._circle3d(0, 0, _hr3, _hr1, 0, 0)
        self._circle3d(0, 0, -_hr1, _hr3, 0, 0)
        self._circle3d(0, 0, -_hr3, _hr1, 0, 0)
        self._circle3d(0, 0, 0, _hr4, _hx4, 0)
        self._circle3d(0, 0, 0, _hr4, _hx4, _hx2)
        self._circle3d(0, 0, 0, _hr4, _hx4, _hx4)
        self._circle3d(0, 0, 0, _hr4, _hx4, -_hx2)
        py5.stroke(255, 0, 0)
        self._line3d(0, 0, 0, 1.5, 0, 0)
        py5.stroke(0, 255, 0)
        self._line3d(0, 0, 0, 0, 1.5, 0)
        py5.stroke(0, 0, 255)
        self._line3d(0, 0, 0, 0, 0, 1.5)

    def _plot_lines(self):
        pass





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
                fn_value  = lambda y: y * 2 - 1.0,
                fn_pretty = lambda y: '{:.2f} m/s'.format(y) )
        graph.set_ys([nan2zero(rss(rec.w)) for rec in records],
                'sensor gyro', icon='g', color=(155,33,0),
                fn_value  = lambda y: y * 0.05 - 1.0,
                fn_pretty = lambda y: '{:d} deg/s'.format(int(y * 180 / math.pi)) )
        graph.set_ys([rec.jumping for rec in records],
                'jumping', icon='J', color=(0,200,0),
                fn_value  = lambda y: -0.01 + 0.02 * int(y),
                fn_pretty = lambda y: 'air' if y else 'grounded' )
        sphere.set_vector(nan2zero(rec0.a),
                'sensor accel', icon='a', color=(255,99,0),
                fn_value  = lambda y: vmul(y, 1),
                fn_pretty = lambda y: '{:.2f} m/s'.format(rss(y)) )
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
