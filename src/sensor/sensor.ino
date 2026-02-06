#include <M5StickCPlus2.h>
#include <esp_now.h>
#include <WiFi.h>

// 受信機のMACアドレスに書き換えないといけない
uint8_t broadcastAddress[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF}; 

bool isSending = false; // 現在送信中かどうかを管理する変数

void setup() {
  M5.begin();
  M5.Imu.init();
  
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();

  if (esp_now_init() != ESP_OK) {
    M5.Lcd.println("ESP-NOW Init Failed");
    return;
  }

  esp_now_peer_info_t peerInfo = {};
  memcpy(peerInfo.peer_addr, broadcastAddress, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;

  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    M5.Lcd.println("Failed to add peer");
    return;
  }

  M5.Lcd.setRotation(3);
  M5.Lcd.fillScreen(BLACK);
  M5.Lcd.println("READY: Press Btn A to Start");
}

void loop() {
  M5.update(); // ボタン状態の更新

  // ボタンAが「押された瞬間」を検知
  if (M5.BtnA.wasPressed()) {
    isSending = !isSending; // trueならfalseに、falseならtrueに入れ替える
    
    // 画面のリセット
    M5.Lcd.fillScreen(isSending ? GREEN : BLACK);
  }

  if (isSending) {
    // データ取得
    float ax, ay, az, gx, gy, gz;
    M5.Imu.getAccelData(&ax, &ay, &az);
    M5.Imu.getGyroData(&gx, &gy, &gz);

    // カンマ区切り文字列作成
    char msg[80]; 
    sprintf(msg, "%.2f,%.2f,%.2f,%.2f,%.2f,%.2f", ax, ay, az, gx, gy, gz);

    // ESP-NOW送信
    esp_now_send(broadcastAddress, (uint8_t *) msg, strlen(msg));

    // 送信中の表示
    M5.Lcd.setCursor(0, 0);
    M5.Lcd.printf("RECORDING...\n%s", msg);
  } else {
    // 停止中の表示
    M5.Lcd.setCursor(0, 0);
    M5.Lcd.println("STOPPED\nPress Btn A to Start");
  }

  delay(10); // 100Hz
}