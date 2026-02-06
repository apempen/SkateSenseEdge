#include <Arduino.h>
#include <WiFi.h>
#include <M5StickCPlus2.h>


void setup() {
  // M5StickC Plus2の初期化
  auto cfg = M5.config();
  M5.begin(cfg);

  // 画面の設定
  M5.Lcd.setRotation(1);       // 画面を横向きにする
  M5.Lcd.fillScreen(BLACK);    // 背景を黒に
  M5.Lcd.setTextColor(WHITE);  // 文字を白に
  M5.Lcd.setTextSize(2);       // 文字サイズを調整

  // MACアドレスの取得
  String mac = WiFi.macAddress();

  // 画面に出力
  M5.Lcd.setCursor(10, 40);    // 表示開始位置 (x, y)
  M5.Lcd.println("MAC Address:");
  M5.Lcd.setCursor(10, 70);
  M5.Lcd.println(mac);

  // シリアルモニタにも一応出しておく
  Serial.println(mac);
}

void loop() {
  M5.update(); // 本体のボタン状態などの更新（今回は表示だけなので空でもOK）
}