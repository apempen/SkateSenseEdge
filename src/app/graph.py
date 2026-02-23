
# 3次元グラフの表示
# py5ライブラリのsetupもしくはdraw関数内で使用してください

import math
import numpy as np
import py5

# utilities

def _pick_color(n):
    # return arbitrary color only depending on n
    # if |n - m| is small enough, _pick_color(n) should be easily distinguished from _pick_color(m)
    return (100, 200, 100)

def _rot_x(th):
    # return rotation matrix 4x4
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
    # return translation matrix 4x4
    return np.array([[ 1,  0,  0,  x],
                     [ 0,  1,  0,  y],
                     [ 0,  0,  1,  z],
                     [ 0,  0,  0,  1]], dtype=float)

def _mkv(x, y, z):
    # make vector from the coordination x y and z
    return np.array([[x], [y], [z], [1]], dtype=float)


# graceful constatns

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


class SphereDrawer:

    # ベクトルの向きと大きさを表示する

    def __init__(self, w, h, *, fontsize=12):
        self.__gw = w                # グラフの幅
        self.__gh = h
        self.__ox = w // 2           # 球の中心座標
        self.__oy = h // 2
        self.__oz = - min(w, h) // 4 * 3
        self.__rr = min(w, h) // 4   # 球の半径
        self.__nn = 16               # テッセレーション
        self.__fs = fontsize         # フォントサイズ
        self.__vecs = []
        # 計算用ベクトル、行列
        self.__mat_r = _rot_x(-math.pi / 10) @ _rot_y(- math.pi / 4) @ _rot_x(math.pi / 2)


    def set_vector(self, vec, name, *, icon=None, color=None, fn_value=None, fn_pretty=None):
        # あるフレームに表示するベクトルを登録する
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
        # 登録したベクトルを消去する
        self.__vecs.clear()

    def scroll(self, dx, dy):
        # 回転する
        #   (0, 0) で無回転、dx はscreen-x方向、dyはscreen-y方向に球を転がす
        self.__mat_r = self._scroll(dx, dy) @ self.__mat_r

    def plot(self, gx, gy, rx=0, ry=0):
        # 描画
        #   gx, gy は描画座標
        #   rx, ry は球の回転
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
        # 回転量を計算する内部関数
        th = math.atan2(dy, dx)
        ph = math.sqrt((dx * dx) + (dy * dy)) / self.__rr
        mat_pp = _rot_z(- th)
        mat_rr = _rot_y(ph)
        return mat_pp.T @ mat_rr @ mat_pp

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
        self._line3d(0, 0, 0, 1.5, 0, 0, fn_weight=self._fnw)
        py5.stroke(0, 255, 0)
        self._line3d(0, 0, 0, 0, 1.5, 0, fn_weight=self._fnw)
        py5.stroke(0, 0, 255)
        self._line3d(0, 0, 0, 0, 0, 1.5, fn_weight=self._fnw)

    def _plot_lines(self):
        for idx, nam, ico, col, vec, cur in reversed(self.__vecs):
            if vec is None:
                continue
            py5.stroke(*col)
            py5.fill(*col)
            py5.text_size(self.__fs)
            _, p2 = self._line3d(0, 0, 0, vec[0], vec[1], vec[2])
            if p2[0] - self.__ox < 0:
                if p2[1] - self.__oy < 0:
                    py5.text_align(py5.RIGHT, py5.BOTTOM)
                else:
                    py5.text_align(py5.RIGHT, py5.TOP)
            else:
                if p2[1] - self.__oy < 0:
                    py5.text_align(py5.LEFT, py5.BOTTOM)
                else:
                    py5.text_align(py5.LEFT, py5.TOP)
            py5.text('{} {}'.format(ico, cur), p2[0], p2[1])
            py5.text_align(py5.LEFT, py5.TOP)
            py5.text('{}: {}'.format(ico, nam), 2, self.__fs * idx + 2)


    # 座標変換
    # - モデル座標: float型の3次元ベクトル。球の中心が(0,0,0)。単位: m
    # - スクリーン座標: int型の3次元ベクトル。画面左上が(0,0,z)。z軸を除いた2次元ベクトルはpy5ライブラリと互換。単位: px
    # どちらも左手系。すなわち、スクリーン座標のz軸は手前側を向く
    # モデルベクトルを$\bm{x}$、スクリーンベクトルを$\bm{y}$として、
    # $$
    #     \bm{w} = R \bm{x} \
    #     \bm{y} = - \frac{ r }{ (\bm{o} / r + \bm{w}) \dot \bm{e}_z } \bm{w} + \bm{o}
    # $$
    # ただし、
    # - $R$: 回転行列。_scroll関数が変更する
    # - $r$[px/m]: モデル空間の単位球の半径
    # - $\bm{o}$[px]: 単位球の位置


    def _screen(self, xx):
        xx = self.__mat_r @ xx
        coef = - self.__rr / (self.__oz / self.__rr + xx[2,0])
        return coef * xx[0,0] + self.__ox, coef * xx[1,0] + self.__oy, coef * xx[2,0] + self.__oz

    def _circle3d(self, ox, oy, oz, rr, rx, ry):
        oo = _mkv(ox, oy, oz)
        di = _rot_x(rx) @ _rot_y(ry)
        points = [self._screen(oo + di @ _rot_z(2 * math.pi * i / self.__nn) @ _mkv(rr, 0, 0)) for i in range(self.__nn)]
        points.append(points[0])
        for i in range(self.__nn):
            py5.line(points[i][0], points[i][1], points[i+1][0], points[i+1][1])
        aa = oo + di @ _mkv(rr, 0, 0)
        bb = self._screen(aa)

    def _line3d(self, x1, y1, z1, x2, y2, z2, *, fn_weight=None):
        # - draw line from (x1, y1, z1) to (x2, y2, z2)
        # - the given coords are in the model space
        # - if fn_weight is given, the line weight will be fn_weight(s1, s2) where
        #     s1, s2 are 3-tuples of the two points in the screen space
        p1 = self._screen(_mkv(x1, y1, z1))
        p2 = self._screen(_mkv(x2, y2, z2))
        if fn_weight is not None:
            w = fn_weight(p1, p2)
            if w is not None:
                py5.stroke_weight(w)
        py5.line(p1[0], p1[1], p2[0], p2[1])
        return p1, p2

    @staticmethod
    def _fnw(p1, p2):
        # p1, p2 should be 3d vectors
        # this functions is meant to be used as a callback of _line3d `fn_weight`
        # returns larger value if (p2 - p1) is facing toward +z
        epsilon = 1e-10  # random value
        magnitude = math.sqrt(sum([(p2[i] - p1[i]) ** 2 for i in range(3)]))
        element_z = (p2[2] - p1[2])
        if magnitude < epsilon:
            return 3
        else:
            reg = element_z / magnitude
        if reg < 0:
            return 1
        elif reg < math.sqrt(2) / 2:
            return 2
        else:
            return 3



