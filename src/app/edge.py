
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
from algorithm import Quaternion, fit_circle, fit_line, estimate_rotation



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
    roll: float          # rad; XYZ軸に対するオイラー角
    pitch: float         # rad
    yaw: float           # rad
    accel: tuple         # 推定された移動加速度
    gravity: tuple       # 推定された重力の向き
    angvel: tuple        # 推定された角速度



# --- public関数の定義 ---
# これらの関数はmain.pyなどからも呼ばれる

# -- 初期化関数たち

def init(port, baudrate, maxlen=10):
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

def calibrate(a0, a1, aa, w0, w1, ww):
    if _calib is not None:
        _calib.calibrate(
                Quaternion.pure(*a0),
                Quaternion.pure(*a1),
                [Quaternion.pure(*a) for a in aa],
                Quaternion.pure(*w0),
                Quaternion.pure(*w1),
                [Quaternion.pure(*w) for w in ww] )
        return True
    else:
        return False


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

class Calibrator:

    def __init__(self):
        self.la = 1.0
        self.lw = 1.0
        self.rot     = Quaternion.identity()
        self.rot_inv = self.rot.inverse()
        self.ba = Quaternion.zero()
        self.bw = Quaternion.zero()

    def transform_a(self, a):
        return self.la * (self.rot @ a) + self.ba

    def transform_w(self, w):
        return self.lw * (self.rot @ w) + self.bw

    def calibrate(self, a0, a1, aa, w0, w1, ww):
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
        rot     = estimate_rotation([az, ay, Quaternion.zero()], [ez, ey, Quaternion.zero()]).conjugate()
        rot_inv = rot.conjugate()
        ba = - la * (rot @ ao)
        bw = - lw * (rot @ wo)

        # done!
        self.la = la
        self.lw = lw
        self.rot     = rot
        self.rot_inv = rot_inv
        self.ba = ba
        self.bw = bw


class Filter:

    # Orientation Estimation Using a Quaternion-Based Indirect Kalman Filter
    #   With Adaptive Estimation of Extenrnal Acceleration
    # doi: 10.1109/TIM.2010.2047157
    # https://ieeexplore.ieee.org/document/5462839
    #
    #   ↑これをやりたかったけど9DOF必要らしい

    def __init__(self):
        # 拡張カルマンフィルタ
        self.t   = 0.0
        self.gravity       = Quaternion.k()
        self.posture       = Quaternion.identity()
        self.body_accel    = Quaternion.zero()
        self.body_velocity = Quaternion.zero()
        # カルマンフィルタ本体
        self.x   = np.zeros(9)  # posture + accel + velocity
        self.P   = np.zeros((9, 9))
        self.Q   = np.zeros((9, 9))
        self.R   = np.zeros((3, 3))

    def set(self, *, gravity=None, q_posture=None, q_accel=None, q_velocity=None, r_accel=None):

        if gravity is not None:
            if isinstance(gravity, Quaternion):
                self.gravity = gravity.imagq()
            else:
                self.gravity = Quaternion.pure(*gravity)

        if q_posture is not None:
            if isinstance(q_posture, np.ndarray):
                self.Q[0:3,0:3] = q_posture.reshape((3,3))
            elif isinstance(q_posture, float|int):
                self.Q[0:3,0:3] = np.diag([q_posture**2] * 3)
            else:
                self.Q[0:3,0:3] = np.diag(q_posture)

        if q_accel is not None:
            if isinstance(q_accel, np.ndarray):
                self.Q[3:6,3:6] = q_accel.reshape((3,3))
            elif isinstance(q_accel, float|int):
                self.Q[3:6,3:6] = np.diag([q_accel**2] * 3)
            else:
                self.Q[3:6,3:6] = np.diag(q_accel)

        if q_velocity is not None:
            if isinstance(q_velocity, np.ndarray):
                self.Q[6:9,6:9] = q_velocity.reshape((3,3))
            elif isinstance(q_velocity, float|int):
                self.Q[6:9,6:9] = np.diag([q_velocity**2] * 3)
            else:
                self.Q[6:9,6:9] = np.diag(q_velocity)

        if r_accel is not None:
            if isinstance(r_accel, np.ndarray):
                self.R[0:3,0:3] = r_accel.reshape((3,3))
            elif isinstance(r_accel, float|int):
                self.R[0:3,0:3] = np.diag([r_accel**2] * 3)
            else:
                self.R[0:3,0:3] = np.diag(r_accel)


    @staticmethod
    def drmat3x3(q):
        return [
            np.array([
                [  4 * q.x,  2 * q.y,  2 * q.z ],
                [  2 * q.y,        0, -2 * q.w ],
                [  2 * q.z,  2 * q.w,        0 ] ]),
            np.array([
                [        0,  2 * q.x,  2 * q.w ],
                [  2 * q.x,  4 * q.y,  2 * q.z ],
                [ -2 * q.w,  2 * q.z,        0 ] ]),
            np.array([
                [        0, -2 * q.w,  2 * q.x ],
                [  2 * q.w,        0,  2 * q.y ],
                [  2 * q.x,  2 * q.y,  4 * q.z ] ]) ]


    def filter(self, t, a, w):

        x = self.x
        P = self.P

        dt = t - self.t
        self.t = t

        # 予測
        rotq = Quaternion.from_axis_angle(w, w.norm() * dt)
        rotm = Quaternion.to_rotation_matrix(rotq)
        x[0:3] = rotq.imag()                    # 角速度により回転させる
        x[3:6] = rotm @ x[3:6]                  # 現状維持
        x[6:9] = rotm @ (x[6:9] + dt * x[3:6])  # 加速度を角速度に
        F = np.zeros((9,9))
        F[0:3,0:3] = np.array([
            [  rotq.w,  rotq.z, -rotq.y ],
            [ -rotq.z,  rotq.w,  rotq.x ],
            [  rotq.y, -rotq.x,  rotq.w ] ])
        F[3:6,3:6] = rotm
        F[6:9,3:6] = dt * rotm
        F[6:9,6:9] = rotm
        P = F @ P @ F.T + self.Q * dt
        # 残差
        z_accel = np.array((a).imag())
        x_accel = np.array((self.posture * rotq @ self.gravity).imag())
        r = z_accel - x_accel
        H = np.zeros((3,9))
        H[0:3,0:3] = np.stack([
            Quaternion.to_rotation_matrix(self.posture) @ drmat @ np.array(self.gravity.imag())
            for drmat in Filter.drmat3x3(rotq) ], axis=1)
        H[0:3,3:6] = np.identity(3)
        S = H @ P @ H.T + self.R
        # 求ゲイン
        K = P @ H.T @ np.linalg.inv(S)
        x = x + K @ r
        P = P - K @ H @ P
        # 事後処理
        self.posture       = (self.posture * Quaternion(1, *x[0:3])).normalized()
        self.body_accel    = Quaternion.pure(*x[3:6])
        self.body_velocity = Quaternion.pure(*x[6:9])
        x[0:3] = 0

        self.x = x
        self.P = P





# global status

_const_g   = 9.80665        # [m/s]
_const_deg = math.pi / 180  # [rad]
_const_ms  = 1 / 1000       # [s]
_jump_count = 0
_calib = Calibrator()
_filter = Filter()

def destroy_memory():
    global _jump_count, _calib, _filter
    # 計算に必要なデータをリセットする
    _jump_count = 0
    _calib = Calibrator()
    _filter = Filter()

    # カルマンフィルタの定数や初期値
    #   単位は s, m/s/s, rad/s など（センサから送られてくる値は ms, g, deg/s なので注意）
    _filter.set(
            q_posture   = 1.5 * _const_deg,   # [rad/s]
            q_accel     = 0.001,             # [m/s/s/s]
            q_velocity  = 0.02,               # [m/s/s/s]
            r_accel     = 0.5,                # [m/s/s]
            gravity     = Quaternion.pure(0, 0, _const_g) )

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
    #tilt = math.atan2(a.z, a.x)   # とりあえずこれで
    jump = False
    if t - 1000 > _jump_count * 1000:
        # 1秒に1回だけジャンプしたことにする
        jump = True
        _jump_count += 1

    # キャリブレーション
    accel   = _calib.transform_a(a)
    angvel  = _calib.transform_w(w)
    # カルマンフィルタ
    _filter.filter(t * _const_ms, accel * _const_g, angvel * _const_deg)
    gravity = _filter.posture @ _filter.gravity / _const_g
    q       = _filter.posture
    accel   = _filter.body_accel
    # 傾きの計算
    R       = Quaternion.to_rotation_matrix(q)
    roll    = math.asin(R[0,2])
    pitch   = math.atan2(-R[1,2], R[2,2]) if math.cos(roll) != 0 else math.atan2(R[2,1], R[1,1])
    yaw     = math.atan2(-R[0,1], R[0,0]) if math.cos(roll) != 0 else 0.0
    tilt    = roll

    return Record(
            a = a.imag(),
            w = w.imag(),
            t = t,
            jump = jump,
            land = False,
            jumping = False,
            tilt = tilt,
            roll = roll,
            pitch = pitch,
            yaw = yaw,
            accel   = accel.imag(),
            angvel  = angvel.imag(),
            gravity = gravity.imag(),
            )

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
    global _last_record
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
            _last_record = record
    except KeyboardInterrupt:
        pass



