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
from graph import GraphDrawer, SphereDrawer, EllipseDrawer  # グラフ表示用のスクリプト
import cv2



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
record_count = 0
records = deque(maxlen=maxlen) # データを溜めるキュー、キューだから過去のデータが消えてく
lastmouse = False
pivotx = 0
pivoty = 0

# 状態遷移を管理する変数
mode = 'normal'
phase = 'normal'
message = 'aa'

# キャリブレーション用のデータ置き場
raw_acc_list  = list()
raw_gyro_list = list()
keyframe1     = None
keyframe2     = None

graph = None
sphere = None
ellipse = None
camera = None           # Camoなどの仮想/実カメラ入力
camera_img = None       # py5へ描画するための画像バッファ
camera_img_w = 0        # バッファ再生成判定用（入力フレーム幅）
camera_img_h = 0        # バッファ再生成判定用（入力フレーム高）

key = 0

show_3d = True


def setup():
    global graph, sphere, ellipse, camera, camera_img, camera_img_w, camera_img_h
    # プログラムの最初に1度だけ呼ばれる
    py5.size(480 * 3, 480)  # ウィンドウサイズ、P3Dとすることで3次元描画が可能
    py5.frame_rate(30)  # カメラ映像の体感遅延を減らすため30fpsで描画
    graph = GraphDrawer(400, 400)
    sphere = SphereDrawer(400, 400)
    ellipse = EllipseDrawer(400,400)

def draw():
    global lastmouse, pivotx, pivoty, show_3d, record_count, camera, camera_img, camera_img_w, camera_img_h
    # プログラム中繰り返し呼ばれる

    # データを読み込む
    tmp = edge.ask_records()
    record_count = len(tmp)                    # この描画フレームで読み込まれたデータ数
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
    py5.text('count: {}'.format(record_count), 480, 20)
    if len(records) != 0:
        py5.text(repr(records[-1]), 10, 410, py5.width - 20, py5.height - 420)
    py5.fill(40)
    py5.text(message, 0, 460, py5.width, 20)

    # プロットするデータを graph, ellipse, sphere などのインスタンスに流し込む
    if len(records) != 0:
        rec0 = records[-1]
        xs = [float(rec.t - rec0.t) / 1000.0 for rec in records]

        # `graph`: 横軸がt（時間）のグラフプロット
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
                'sensor gyro', icon='w', color=(155,33,0),
                fn_value  = lambda y: y * math.pi / 180 * 0.2 - 1.0,
                fn_pretty = lambda y: '{:d} deg/s'.format(int(y)) )
        graph.set_ys([nan2zero(rss(rec.accel)) for rec in records],
                'calib accel', icon='A', color=(255,99,0),
                fn_value  = lambda y: y * 0.4 - 1.0,
                fn_pretty = lambda y: '{:.2f} G'.format(y) )
        graph.set_ys([nan2zero(rss(rec.angvel)) for rec in records],
                'calib gyro', icon='W', color=(155,33,0),
                fn_value  = lambda y: y * math.pi / 180 * 0.2 - 1.0,
                fn_pretty = lambda y: '{:d} deg/s'.format(int(y)) )
        graph.set_ys([rec.jumping for rec in records],
                'jumping', icon='J', color=(0,200,0),
                fn_value  = lambda y: -0.01 + 0.02 * int(y),
                fn_pretty = lambda y: 'air' if y else 'grounded' )

        # `ellipse`: xz平面の空間プロット（ブレードの角度）
        th = - rec0.tilt
        if math.isnan(th):
            th = 0.0
        shoex = math.cos(th + math.pi/2)
        shoey = math.sin(th + math.pi/2)
        ellipse.plot_point(shoex, shoey,
                'The Blade ({:d} deg)'.format(int(th * 180 / math.pi)),
                icon='A', color=(255, 99, 0) )

        # `sphere`: xyz空間の3次元プロット（重力や加速度など）
        sphere.set_vector(nan2zero(rec0.a),
                'sensor accel', icon='a', color=(255,99,0),
                fn_value  = lambda y: vmul(y, 1.0),
                fn_pretty = lambda y: '{:.2f} G'.format(rss(y)) )
        sphere.set_vector(nan2zero(rec0.w),
                'sensor gyro', icon='w', color=(155,33,0),
                fn_value  = lambda y: vmul(y, math.pi / 180 * 0.4),
                fn_pretty = lambda y: '{:d} deg/s'.format(int(rss(y))) )
        sphere.set_vector(nan2zero(rec0.accel),
                'calib accel', icon='A', color=(255,99,0),
                fn_value  = lambda y: vmul(y, 1.0),
                fn_pretty = lambda y: '{:.2f} G'.format(rss(y)) )
        sphere.set_vector(nan2zero(rec0.angvel),
                'calib gyro', icon='W', color=(155,33,0),
                fn_value  = lambda y: vmul(y, math.pi / 180 * 0.4),
                fn_pretty = lambda y: '{:d} deg/s'.format(int(rss(y))) )
        sphere.set_vector(nan2zero(rec0.gravity),
                'calib gravity', icon='G', color=(0, 0, 0),
                fn_value  = lambda y: vmul(y, 1.0),
                fn_pretty = lambda y: '{:.2f} G'.format(rss(y)) )

    # 流し込まれたデータやキャプチャされたカメラ画像を画面に表示
    if camera is not None:
        # grab/retrieveを使ってキュー内の古いフレームを捨て、遅延を減らす
        ok = False
        frame = None
        for _ in range(2):
            if not camera.grab():
                break
            ok, frame = camera.retrieve()
        if ok:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w = frame_rgb.shape[:2]
            if camera_img is None or camera_img_w != w or camera_img_h != h:
                # 入力解像度が変わったときだけpy5画像を作り直す
                camera_img = py5.create_image(w, h, py5.RGB)
                camera_img_w = w
                camera_img_h = h
            camera_img.set_np_pixels(frame_rgb, bands="RGB")
            # 左ペイン(400x400)に縦横比を保ったまま収め、右側表示と重ならないようにする
            box_x = 40
            box_y = 0
            box_w = 400
            box_h = 400
            scale = min(box_w / w, box_h / h)
            draw_w = int(w * scale)
            draw_h = int(h * scale)
            draw_x = box_x + (box_w - draw_w) // 2
            draw_y = box_y + (box_h - draw_h) // 2
            py5.fill(246)
            py5.stroke(0)
            py5.rect(box_x, box_y, box_w, box_h)
            py5.image(camera_img, draw_x, draw_y, draw_w, draw_h)

    if show_3d:
        sphere.plot(480, 0, rx, ry)
    else:
        ellipse.plot(480,0)

    graph.plot(960, 0)

    # リソース解放（軽微なデバッグ）
    graph.reset()
    sphere.reset()
    ellipse.reset()
    
        # カーソル描画
    py5.stroke(255, 0, 0)
    py5.fill(255)
    py5.ellipse(py5.mouse_x, py5.mouse_y, 4, 4)

    # 最大値を表示
    py5.stroke(0,0,0)
    py5.fill(0,0,0)
    maxacc = max([rss(rec.a) for rec in records])
    py5.text('maximum acc. cpt. {:7.3f} G'.format(maxacc), 500, 321)
    maxang = max([rss(rec.w) for rec in records])
    py5.text('maximum ang. cpt. {:7.3f} deg/s'.format(maxang), 500, 334)
    
    # その他
    on_calibration()
    

def key_pressed():
    global show_3d
    # スペースキーを押すたびに2Dと3Dをトグル（切り替え）する
    if py5.key == ' ':
        show_3d = not show_3d
    # 特定のキーで直接切り替えたい場合は以下のようにします
    elif py5.key == '2':
        show_3d = False
    elif py5.key == '3':
        show_3d = True
    elif py5.key == 'c':
        # キャリブレーション開始
        if mode == 'normal' or mode == 'calibration':
            do_calibration()


def do_calibration():
    global mode, phase, message, raw_acc_list, raw_gyro_list, keyframe1, keyframe2

    # initiation
    if mode == 'normal':
        mode = 'calibration'
        phase = 0
        raw_acc_list = list()
        raw_gyro_list = list()
        keyframe1 = None
        keyframe2 = None
    elif mode == 'calibration':
        phase += 1
    else:
        return

    if phase == 0:
        message = 'Calibrating sensors... Place the blade on the ground, hold the shoe upright and press the C key'
    elif phase == 1:
        keyframe1 = len(raw_acc_list)
        message = 'Calibrating sensors... Keep the blade on the ground, gently decline the shoe to the right and press the C key'
    elif phase == 2:
        keyframe2 = len(raw_acc_list)
        message = 'Calibrating sensors... Keep the blade on the ground, gently decline the shoe to the left and press the C key'
    else:
        a0 = calibration_agg(raw_acc_list, keyframe1)
        a1 = calibration_agg(raw_acc_list, keyframe2)
        w0 = calibration_agg(raw_gyro_list, keyframe1)
        w1 = calibration_agg(raw_gyro_list, keyframe2)
        aa = calibration_spr(raw_acc_list, 30)
        ww = calibration_spr(raw_gyro_list, 30)
        edge.calibrate(a0, a1, aa, w0, w1, ww)
        message = 'Perfect!'
        mode = 'normal'

def on_calibration():
    global mode, phase, message, raw_acc_list, raw_gyro_list, keyframe1, keyframe2
    if mode == 'calibration':
        for i in range(record_count):
            raw_acc_list.append(records[-record_count+i].a)
            raw_gyro_list.append(records[-record_count+i].w)


def calibration_agg(ls, kf, w=5):
    # リストの kf 番目の要素の前後を平均する
    #   ただしリストの要素型は tuple[float|int, float|int, float|int]
    ls = ls[kf-w:kf+w]
    n = len(ls)
    if n == 0:
        return (0, 0, 0)
    x = y = z = 0
    for item in ls:
        x += item[0]
        y += item[1]
        z += item[2]
    return (x / n, y / n, z / n)

def calibration_spr(ls, n):
    # リストの中から n 個残して間引く
    retval = list()
    m = len(ls)
    if m <= n:
        return ls.copy()
    d = m / n
    for i in range(n):
        retval.append(ls[int(d * i)])
    return retval


def exiting():
    global camera, camera_img, camera_img_w, camera_img_h
    if camera is not None:
        camera.release()
        camera = None
    # 再実行時の状態混入を避けるため、画像バッファ情報も初期化
    camera_img = None
    camera_img_w = 0
    camera_img_h = 0




if __name__ == '__main__':

    try:
        port = sys.argv[1]
        camid = int(sys.argv[2]) if len(sys.argv) >= 3 else None
        baudrate = 115200
    except (TypeError, IndexError):
        print('usage: {} PORT [CAMERA_ID]'.format(sys.argv[0]), file=sys.stderr)
        exit(254)

    if camid is not None:
        print('# trying to init camera {}...'.format(camid))
        # 更新: 実行時引数 CAMERA_ID でキャプチャするカメラを選択できます
        camera = cv2.VideoCapture(camid)  # Camo側で認識されたカメラindex この部分は0か1か2になる。自分は0にしたらPCのカメラが映った
        if camera is None or not camera.isOpened():
            print('#   failed...')
            camera = None
        else:
            print('#   succeeded!')
            # 遅延対策: バッファを浅くし、古いフレームが溜まりにくい設定にする
            camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            camera.set(cv2.CAP_PROP_FPS, 30)
            camera_img = None
            camera_img_w = 0
            camera_img_h = 0
    else:
        camera = None

    rc = edge.init(port, baudrate)
    if rc != 0:
        exit(rc)
    py5.run_sketch()
