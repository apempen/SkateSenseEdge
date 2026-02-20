#!/usr/bin/env python3

import os
import sys
import edge 
import csv 
import time

def main():
    if len(sys.argv) != 2:
        print('Usage: python {} PORT'.format(sys.argv[0]), file=sys.stderr)
        sys.exit(254)
        
    port = sys.argv[1]
    baudrate = 115200
    
    rc = edge.init(port, baudrate)
    if rc != 0:
        print("Error: Failed to initialize serial connection.", file=sys.stderr)
        sys.exit(rc)

    # 設定：何回受信したら終了するか
    MAX_RECORDS = 100
    record_count = 0

    print(f"Recording {MAX_RECORDS} data points from {port} to out.csv ...")

    filename = 'out.csv'
    with open(filename, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        
        header = ['time_ms', 'accel_x', 'accel_y', 'accel_z', 'gyro_x', 'gyro_y', 'gyro_z', 'tilt', 'is_jump']
        writer.writerow(header)
        
        keep_running = True
        try:
            while keep_running:
                records = edge.ask_records()
                print("records:", records)
                if records:
                    for record in records:
                        # データをリスト化して書き込み
                        row = [
                            record.t, record.a[0], record.a[1], record.a[2],
                            record.w[0], record.w[1], record.w[2],
                            record.tilt, int(record.jump)
                        ]
                        writer.writerow(row)
                        
                        # カウントを増やす
                        record_count += 1
                        
                        # 指定回数に達したら終了
                        if record_count >= MAX_RECORDS:
                            print(f"\nReached {MAX_RECORDS} records. Finishing...")
                            keep_running = False
                            break 
                    
                    # 進捗表示（1000件ごとなど）
                    if record_count % 1000 == 0:
                        print(f"Progress: {record_count} / {MAX_RECORDS}")
                    
                    f.flush()

                time.sleep(0.01)

        except KeyboardInterrupt:
            print("\nStopped by user.")

    print(f"Done. Saved {record_count} records to {filename}")

if __name__ == '__main__':
    main()