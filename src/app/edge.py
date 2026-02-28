
"""
edge.py
=======

センサから送られてきた値を①受け取り、②計算し、③ためておくためのクラスを定義する。
角度の計算やキャリブレーションなど、描画に関係ないことはこっちのファイルに書き込むといいかも。

- `init` シリアルポートなどの初期化
- `ask_records` データの取得
- `make_record` ブレードの角度などを計算する

"""
import sys
import math
import time
import serial
#import serial.tools.list_ports
import threading
from collections import deque
from dataclasses import dataclass
import itertools
import numpy as np
from algorithm import Quaternion, fit_circle, fit_line


# --- グローバル変数の定義 ---

_thread = None           # スレッド
_ser = None              # USBポート
_queue = deque()         # データをためておくキュー
_t0 = 0                  # 時間の原点
_last_record = None      # 前回のレコード


@dataclass(frozen=True)  # 構造体Recordを定義
class Record:
    # センサから送られてきた値
    a: tuple             # 加速度
    w: tuple             # 角速度
    # 計算に使用される値
    t: int               # 時刻（ミリ秒）
    # 計算された値
    jump: bool           # ジャンプした瞬間にTrue、それ以外ではFalse
    land: bool           # 着地の瞬間にTrue、それ以外ではFalse
    jumping: bool        # ジャンプ中にTrue
    tilt: float          # ブレードの傾き
    accel: tuple         # 推定された移動加速度
    gravity: tuple       # 推定された重力の向き
    angvel: tuple        # 推定された角速度



# --- public関数の定義 ---
# これらの関数はmain.pyなどからも呼ばれる

# -- 初期化関数たち

def init(port, baudrate, maxlen=100):
    global _thread, _ser, _queue, _t0, _last_record

    # check for the existing thread
    if _thread is not None:
        print('# already listening the serial')
        return 1

    # open serial
    print('# try to open serial port {} (baudrate={})'.format(port, baudrate))
    _ser = open_serial(port, baudrate)
    if _ser is not None:
        print('#   succeeded!')
    else:
        print('#   failed...')
        return 1

    # create queue
    _queue = deque(maxlen=maxlen)

    # init other variables
    clear()
    set_gravity((0.0, 0.0, 1.0))

    # run the thread
    _thread = threading.Thread(target=_job, daemon=True)
    _thread.start()

    return 0

def clear():
    # ためているデータを空にする
    global _queue, _t0, _last_record
    _queue.clear()
    _t0 = get_time_ms()
    _last_record = None
    destroy_memory()

def get_time_ms():
    # what time is it now? (milliseconds, integer)
    return math.floor(time.time() * 1000)


# -- データ取得

def ready():
    # データがあればTrue
    return len(_queue) != 0

def ask_record():
    # データがあれば返す。無ければNoneを返す
    try:
        return _queue.popleft()
    except IndexError:
        return None

def ask_records():
    # 今あるデータのリストを返す。
    return list(itertools.takewhile(
        lambda x: x is not None,
        (ask_record() for _ in itertools.count()) ))


# --- private関数の定義 ---
# これらの関数はこのスクリプト内から呼ばれる

# -- データの計算

_jump_count = 0
_calib = Calibrator()

def destroy_memory():
    global _jump_count, _calib
    # 計算に必要なデータをリセットする
    _jump_count = 0
    _calib = Calibrator()

def make_record(sensor: list):
    global _jump_count
    # センサから送られてきた値（float型のlist）を用いていろんな計算をする

    a = Quaternion.pure(sensor[0], sensor[1], sensor[2])  # 加速度計 (ax, ay, az)
    w = Quaternion.pure(sensor[3], sensor[4], sensor[5])  # 角速度計 (wx, wy, wz)
    t = get_time_ms() - _t0                 # 時間（整数、ミリ秒）
    if _last_record is not None:
        dt = t - _last_record.t             # 経過時間
    else:
        dt = 0

    # *** 計算する
    tilt = math.atan2(a.z, a.x)   # とりあえずこれで
    jump = False
    if t - 1000 > _jump_count * 1000:
        # 1秒に1回だけジャンプしたことにする
        jump = True
        _jump_count += 1

    accel  = _calib.transform_a(a)
    angvel = _calib.transform_w(w)

    return Record(
            a = a.imag(),
            w = w.imag(),
            t = t,
            jump = jump,
            land = False,
            jumping = False,
            tilt = tilt,
            accel   = accel.imag(),
            angvel  = angvel.imag(),
            gravity = (0.0, 0.0, 0.0,),
            )

class Calibrator:

    def __init__(self):
        self.la = 1.0
        self.lw = 1.0
        self.rot     = Quaternion.identity()
        self.rot_inv = self.rot.inverse()
        self.ba = Quaternion.zero()
        self.bw = Quaternion.zero()

    def transform_a(a):
        return self.la * (self.rot @ a) + self.ba

    def transform_w(w):
        return self.lw * (self.rot @ w) + self.bw

    def calibrate(a0, a1, aa, w0, w1, ww):
        # aa is a list of raw accelaration data and ww is a list of raw angular velocity
        #   (a0, w0) is sensor values which is sent while the device is settled on flat surface
        #   (a1, w1) is sensor values which is sent while the device is inclined to the right
        #   aa must align as a circle and ww must align as a line
        #   then estimate
        #     - the rotation (self.rot),
        #     - the scale factors (self.la, self.lw), and
        #     - the biases (self.ba, self.bw)
        circle = fit_circle(aa)
        line = fit_line(ww)
        ao = circle.center
        r0 = circle.estimate(a0) - ao
        r1 = circle.estimate(a1) - ao
        wo = line.estimate(w0)
        d0 = line.direction

        # let's calibrate!
        la = 1 / r0.norm()
        lw = 1.0
        az = r0.normalized()
        ay = Quaternion.cross(r0, r1).normalized()  # cross product
        wy = d0.normalized() if Quaternion.dot(d0, ay) >= 0 else - d0.normalized()  # reverse the direction depending on the dot product
        ez = Quaternion.k()
        ey = Quaternion.j()
        rot     = estimate_rotation([az, ay], [ez, ey])
        rot_inv = W.conjugate()
        ba = - (rot @ ao)
        bw = - (rot @ wo)

        # done!
        self.la = la
        self.lw = lw
        self.rot     = rot
        self.rot_inv = rot_inv
        self.ba = ba
        self.bw = bw





# -- その他

def open_serial(port, baudrate, skip_some=True):
    try:
        # timeout=1.0 を追加（1秒間データが来なければ readline を抜ける）
        ser = serial.Serial(port=port, baudrate=baudrate, timeout=1.0)
    except serial.SerialException as e:
        print('SerialException:', e, file=sys.stderr)
        return None # 前述の通り None に修正
    
    if not ser.is_open:
        ser.open()

    if skip_some:
        print("# Cleaning buffer...")
        for _ in range(3):
            line = ser.readline() # 1秒待って来なければ次へ行く
            print(f"# Initial line: {line}") # 何か受信できているか確認用
            
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


def _job():
    # thread job
    try:
        # 無限ループ
        for i in itertools.count():
            # read one line
            line = _ser.readline()
            data = parse_line(line)
            # 値の計算を行う
            record = make_record(data)
            _queue.append(record)
    except KeyboardInterrupt:
        pass



