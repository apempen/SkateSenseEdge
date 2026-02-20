
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


# --- グローバル変数の定義 ---

_thread = None           # スレッド
_ser = None              # USBポート
_queue = deque()         # データをためておくキュー
_t0 = 0                  # 時間の原点
_g0 = (0.0, 0.0, 1.0,)   # 静止時の重力の大きさと向き（キャリブレーション）
_last_record = None      # 前回のレコード


@dataclass(frozen=True)  # 構造体Recordを定義
class Record:
    # センサから送られてきた値
    a: tuple             # 加速度
    w: tuple             # 角速度
    # 計算に使用される値
    t: int               # 時刻（ミリ秒）
    g: tuple             # 静止時の重力の大きさと向き（キャリブレーション）
    # 計算された値
    jump: bool           # ジャンプした瞬間にTrue、それ以外ではFalse
    land: bool           # 着地の瞬間にTrue、それ以外ではFalse
    jumping: bool        # ジャンプ中にTrue
    tilt: float          # ブレードの傾き
    gravity: tuple       # 推定された重力の向き
    accel: tuple         # 推定された移動加速度


# --- public関数の定義 ---
# これらの関数はmain.pyなどからも呼ばれる

# -- 初期化関数たち

def init(port, baudrate, maxlen=100):
    global _thread, _ser, _queue, _t0, _g0, _last_record

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

def set_gravity(g):
    # 重力方向を指定する
    global _g0
    if not (isinstance(g, tuple) and len(g) == 3 and all((isinstance(x, float) for x in g))):
        raise TypeError('g must be tuple[float,float,float]')
    _g0 = g

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

def destroy_memory():
    global _jump_count
    # 計算に必要なデータをリセットする
    _jump_count = 0

def make_record(sensor: list):
    global _jump_count
    # センサから送られてきた値（float型のlist）を用いていろんな計算をする

    a = (sensor[0], sensor[1], sensor[2],)  # 加速度計 (ax, ay, az)
    w = (sensor[3], sensor[4], sensor[5],)  # 角速度計 (wx, wy, wz)
    t = get_time_ms() - _t0                 # 時間（整数、ミリ秒）
    g = _g0                                 # 静止時の重力
    if _last_record is not None:
        dt = t - _last_record.t             # 経過時間
    else:
        dt = 0

    # *** 計算する
    tilt = math.atan2(a[2], a[0])   # とりあえずこれで
    jump = False
    if t - 1000 > _jump_count * 1000:
        # 1秒に1回だけジャンプしたことにする
        jump = True
        _jump_count += 1

    return Record(
            a=a, w=w, t=t, g=g,
            jump=jump,
            land=False,
            jumping=False,
            tilt=tilt,
            accel=(0.0, 0.0, 0.0),
            gravity=(0.0, 0.0, 0.0),
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



