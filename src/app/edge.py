
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

    def __init__(self):
        self.q   = Quaternion.identity()
        self.g   = Quaternion.k()
        self.t   = 0.0
        self.x   = np.zeros((9, 1), dtype=float)        # 9x1
        self.P   = np.identity(9, dtype=float)          # 9x9
        self.Rg  = np.zeros((3, 3), dtype=float)        # 3x3
        self.Ra  = np.zeros((3, 3), dtype=float)        # 3x3
        self.Qbg = np.zeros((3, 3), dtype=float)        # 3x3
        self.Qba = np.zeros((3, 3), dtype=float)        # 3x3
        self.Q   = np.zeros((9, 9), dtype=float)        # 9x9
        self.R   = np.zeros((3, 3), dtype=float)        # 3x3
        self.Qab = np.identity(3, dtype=float)          # 3x3
        self.za  = Quaternion.zero()
        self.zg  = Quaternion.zero()
        self.ab  = Quaternion.zero()
        self.ag  = Quaternion.zero()
        self.M1  = 3
        self.r_series = deque(maxlen=self.M1)
        self.M2  = 2
        self.d_series = deque(maxlen=self.M2+1)
        self.gamma = 0.1


    def set_parameters(self, gravity, gamma, M1, M2):

        self.q = Quaternion.identity()
        self.t = 0.0

        if not isinstance(gravity, Quaternion):
            raise TypeError('must be Quaternion')
        else:
            self.g = gravity

        if not isinstance(gamma, float|int):
            raise TypeError('must be float')
        else:
            self.gamma = float(gamma)

        if not isinstance(M1, int):
            raise TypeError('must be int')
        else:
            self.M1 = int(M1)
            self.r_series = deque(maxlen=self.M1)

        if not isinstance(M2, int):
            raise TypeError('must be int')
        else:
            self.M2 = int(M2)
            self.d_series = deque(maxlen=self.M2+1)


    def set_initial_values(self, x, P):

        if not isinstance(x, np.ndarray):
            raise TypeError('must be np.ndarray')
        elif x.shape == (9, 1):
            self.x = np.array(x, dtype=float)
        elif x.shape == (1, 9):
            self.x = np.array(x, dtype=float).T
        elif x.shape == (9,):
            self.x = np.array([[item] for item in x], dtype=float)
        else:
            raise ValueError('shape must be (9, 1), (9, 1) or 9')

        if not isinstance(P, np.ndarray):
            raise TypeError('must be np.ndarray')
        elif P.shape != (9, 9):
            raise ValueError('shape must be (9, 9)')
        else:
            self.P = np.array(P, dtype=float)

    def set_process_noise(self, Qbg, Qba):

        self.Qab = np.zeros((3, 3), dtype=float)

        if not isinstance(Qbg, np.ndarray):
            raise TypeError('must be np.ndarray')
        elif Qbg.shape != (3, 3):
            raise ValueError('shape must be (3, 3)')
        else:
            self.Qbg = np.array(Qbg, dtype=float)
            self.Q[3:6, 3:6] = self.Qbg

        if not isinstance(Qba, np.ndarray):
            raise TypeError('must be np.ndarray')
        elif Qba.shape != (3, 3):
            raise ValueError('shape must be (3, 3)')
        else:
            self.Qba = np.array(Qba, dtype=float)
            self.Q[6:9, 6:9] = self.Qba

    def set_observation_noise(self, Rg, Ra):

        if not isinstance(Rg, np.ndarray):
            raise TypeError('must be np.ndarray')
        elif Rg.shape != (3, 3):
            raise ValueError('shape must be (3, 3)')
        else:
            self.Rg = np.array(Rg, dtype=float)
            self.Q[0:3, 0:3] = 0.25 * self.Rg

        if not isinstance(Ra, np.ndarray):
            raise TypeError('must be np.ndarray')
        elif Ra.shape != (3, 3):
            raise ValueError('shape must be (3, 3)')
        else:
            self.Ra = np.array(Ra, dtype=float)
            self.R[0:3, 0:3] = self.Ra


    def filter(self, t, ya, yg):
        # t  は経過時間
        # ya は観測された加速度
        # yg は観測された角速度

        x  = self.x
        P  = self.P
        T  = t - self.t

        za = ya - self.q @ self.g  # (22)
        za = np.array(za.imag()).reshape(3,1)
        zg = yg
        zg = np.array(zg.imag()).reshape(3,1)
        self.za = Quaternion.pure(*za)
        self.zg = Quaternion.pure(*zg)

        A  = np.zeros((9, 9))
        A[0:3, 0:3] = - Filter.carry_cross(yg)
        A[0:3, 3:6] = - 0.5 * np.identity(3)   # (9)
        ph = np.identity(9) + T * A + 0.5 * T**2 * (A @ A)
        Qd = T * self.Q + 0.5 * (A @ self.Q) + 0.5 * (self.Q @ A.T)  # (16)
        x_ = x
        x  = ph @ x
        printval = x - x_
        P  = ph @ P @ ph.T + Qd  # (17)
        H  = np.zeros((3, 9))
        H[0:3, 0:3] = 2 * Filter.carry_cross(self.q @ self.g)
        H[0:3, 6:9] = np.identity(3)
        S  = H @ P @ H.T + self.R
        K  = P @ H.T @ np.linalg.inv(S + self.Qab)
        r  = za - H @ x
        L  = np.identity(9) - K @ H
        x  = x + K @ r
        P  = L @ P @ L.T + K @ (self.R + self.Qab) @ K.T  # (19)
        qe = Quaternion(1, *x[0:3,0])
        bg = Quaternion.pure(*x[3:6,0])
        ba = Quaternion.pure(*x[6:9,0])
        x[0:3,0] = 0    # (20)

        np.set_printoptions(linewidth=220)
        print(printval.reshape(-1))

        self.r_series.append(r @ r.T)
        U = sum(self.r_series) / len(self.r_series)  # (30)
        ll, uu = np.linalg.eig(U)
        ll = [float(ll[i]) for i in range(len(ll))]
        mm = [float(uu[:,i].T @ S @ uu[:,i]) for i in range(len(ll))]
        dd = [ll[i] - mm[i] for i in range(len(ll))]
        self.d_series.append(max(dd))
        if max(self.d_series) < self.gamma:
            self.Qab = 0  # not moving  # (34)
        else:
            self.Qab = sum([max(dd[i], 0) * uu[:,i] @ uu[:,i].T for i in range(len(ll))])  # (35)

        #assert len(ll) == 3, len(ll)
        #print('~ Qab:{:.4g} len:{} ll:[{:.4g},{:.4g},{:.4g}] uu:[{:.4g},{:.4g},{:.4g}] mm:[{:.4g},{:.4g},{:.4g}] dd:[{:.4g},{:.4g},{:.4g}] r_series:{} d_series:{}'.format(
            #np.linalg.norm(self.Qab), len(ll), *ll, *[np.linalg.norm(uu[:,i]) for i in range(len(ll))], *mm, *dd, len(self.r_series), len(self.d_series)))

        self.q = (self.q * qe.normalized()).normalized()  # (20)
        kkkk = list(map(abs, K.reshape(-1)))
        print('{:9.4f} {:9.4f} {:9.4f}'.format(max(kkkk), min(kkkk), sum(kkkk) / len(kkkk)))

        ab = ya - self.q @ self.g - ba
        ag = self.q @ self.g
        gy = yg - bg

        self.t = t
        self.x = x
        self.P = P
        self.ab = ab    # accel of move
        self.ag = ag    # accel of gravity
        self.gy = gy    # gyro

    @staticmethod
    def carry_cross(q):
        # return $[q\cross]$
        return np.array([
            [    0, -q.z,  q.y ],
            [  q.z,    0, -q.x ],
            [ -q.y,  q.x,    0 ] ])



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
    # ------------ (後で消す)
    try:
        raise OSError()
        with open('ignore/cap1.log', 'r') as f:
            text = f.read()
        items = list()
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            items.append(list(map(float, line.split(','))))
        aa = [Quaternion.pure(x, y, z) for _,x,y,z,_,_,_ in items]
        ww = [Quaternion.pure(x, y, z) for _,_,_,_,x,y,z in items]
        a0 = sum(aa[100:110], Quaternion.zero()) / 10
        a1 = sum(aa[240:250], Quaternion.zero()) / 10
        w0 = sum(ww[100:110], Quaternion.zero()) / 10
        w1 = sum(ww[240:250], Quaternion.zero()) / 10
        _calib.calibrate(a0, a1, aa, w0, w1, ww)
    except OSError:
        pass
    print('!!!! PLEASE REMOVE ME LATER!!!!! from edge.py destroy_memory()')
    # ------------

    # カルマンフィルタの定数や初期値
    #   単位は s, m/s/s, rad/s など（センサから送られてくる値は ms, g, deg/s なので注意）
    gravity = Quaternion.pure(0, 0, _const_g)  # 重力の向きと大きさ [m/s/s]
    gamma   = 2.0                              # 移動判定の閾値
    M1      = 3                                # 移動判定のノイズ耐性を高める
    M2      = 2                                # 移動判定解除までの猶予
    _filter.set_parameters(gravity=gravity, gamma=gamma, M1=M1, M2=M2)
    qe_stdev = 1.0 * _const_deg                 # 角度ドリフトの大きさの初期値 [rad/s]
    bg_stdev = 1.0 * _const_deg                 # 角速度センサのドリフトの大きさの初期値 [rad/s/s]
    ba_stdev = 0.2 * _const_g                        # 加速度センサのドリフトの大きさの初期値 [m/s/s/s]
    _filter.set_initial_values(
            x = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
            P = np.diag([qe_stdev**2] * 3 + [bg_stdev**2] * 3 + [ba_stdev**2] * 3) )
    qbg_stdev = 1e-10                           # 角速度センサのドリフトの大きさ [rad/s/s]
    qba_stdev = 1e-10                           # 加速度センサのドリフトの大きさ [m/s/s/s]
    _filter.set_process_noise(
            Qbg = np.diag([qbg_stdev**2] * 3),
            Qba = np.diag([qba_stdev**2] * 3) )
    rg_stdev = 1 * _const_deg                  # 角速度ノイズの大きさ [rad/s]
    ra_stdev = 0.5                             # 加速度ノイズの大きさ [m/s/s]
    _filter.set_observation_noise(
            Rg = np.diag([rg_stdev**2] * 3),
            Ra = np.diag([ra_stdev**2] * 3) )


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
    _filter.filter(t * _const_ms, a * _const_g, w * _const_deg)
    accel   = _filter.ab / _const_g
    gravity = _filter.ag / _const_g
    angvel  = _filter.gy / _const_deg
    q       = _filter.q
    # 傾きの計算
    R       = Quaternion.to_rotation_matrix(q)
    roll    = np.arcsin(R[0,2])
    pitch   = np.arctan2(-R[1,2], R[2,2]) if np.cos(roll) != 0 else np.arctan2(R[2,1], R[1,1])
    yaw     = np.arctan2(-R[0,1], R[0,0]) if np.cos(roll) != 0 else 0.0
    tilt    = 90 + roll / _const_deg

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



