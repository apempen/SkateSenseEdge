import serial
import csv
import time
import sys
import datetime

# --- 設定 ---
BAUD_RATE = 115200  

def main():
    # コマンドライン引数からポート名を取得
    if len(sys.argv) != 2:
        print(f"使い方が間違っています。\n使用例: python {sys.argv[0]} COM3")
        return

    port_name = sys.argv[1]

    # ファイル名を生成 (例: data_20240217_120000.csv)
    filename = datetime.datetime.now().strftime("data_%Y%m%d_%H%M%S.csv")

    try:
        # シリアルポートを開く
        ser = serial.Serial(port_name, BAUD_RATE, timeout=1)
        print(f"接続完了: {port_name}")
        print(f"保存先: {filename}")
        print("停止するには Ctrl + C を押してください...")

        # バッファのクリア（接続直後のゴミデータを捨てる）
        ser.reset_input_buffer()
        time.sleep(1)

        # CSVファイルを作成して書き込み開始
        with open(filename, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # ヘッダー（1行目の項目名）を書き込む
            header = ["elapsed_time(ms)", "ax", "ay", "az", "gx", "gy", "gz"]
            writer.writerow(header)

            # 計測開始時刻
            start_time = time.time()

            while True:
                if ser.in_waiting > 0:
                    try:
                        # 1行読み取り、デコードして空白削除
                        line = ser.readline().decode('utf-8').strip()
                        
                        # 空行でなければ処理
                        if line:
                            # 経過時間を計算 (ミリ秒)
                            elapsed = (time.time() - start_time) * 1000
                            
                            # カンマ区切りのデータをリストに変換
                            data_list = line.split(',')
                            
                            # データの個数が正しいかチェック
                            if len(data_list) == 6:
                                # 時間を先頭に追加して書き込み
                                row = [f"{elapsed:.2f}"] + data_list
                                writer.writerow(row)
                                
                                # 動作確認用に画面にも少し表示
                                print(f"保存中: {row}")
                            
                    except UnicodeDecodeError:
                        # 通信ノイズなどで文字化けした場合は無視する
                        pass

    except serial.SerialException as e:
        print(f"エラー: ポート {port_name} を開けませんでした。")
        print(e)
    except KeyboardInterrupt:
        print("\n終了します。")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("ポートを閉じました。")

if __name__ == "__main__":
    main()