#include <M5StickCPlus2.h>
#include <esp_now.h>
#include <WiFi.h>


#define MSGBUFFER_LENGTH 255

// 受信機のMACアドレスに書き換えないといけない
uint8_t targetAddress[] = {0x4c,0xc3,0x82,0x9b,0xab,0x34}; 

bool isSending = true; // 現在送信中かどうかを管理する変数
uint16_t sendCount = 0;    // 送信回数
bool sendError = false; 

void setup() {
  M5.begin();
  M5.Imu.init();
  setCpuFrequencyMhz(80); // 省電力化 https://msr-r.net/m5stickc-mobilebattery/
  M5.Display.setBrightness(4); // 省電力化
  
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();

  if (esp_now_init() != ESP_OK) {
    M5.Lcd.println("ESP-NOW Init Failed");
    return;
  }

  esp_now_peer_info_t peerInfo = {};
  memcpy(peerInfo.peer_addr, targetAddress, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;

  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    M5.Lcd.println("Failed to add peer");
    return;
  }

  M5.Lcd.fillScreen(BLACK);
  M5.Lcd.setRotation(1);
  M5.Lcd.setTextColor(GREEN);
  M5.Lcd.setFont(&fonts::FreeSansBold9pt7b);
  M5.Lcd.println("READY");
  // M5.Lcd.println("Press Btn A to Start");
}

void loop() {
  M5.update(); // ボタン状態の更新

  // ボタンAが「押された瞬間」を検知
  // if (M5.BtnA.wasPressed()) {
  //   isSending = !isSending; // trueならfalseに、falseならtrueに入れ替える
  //   sendError = false;
  // }

  if (isSending) {
    // データ取得
    float ax, ay, az, gx, gy, gz;
    M5.Imu.getAccelData(&ax, &ay, &az);
    M5.Imu.getGyroData(&gx, &gy, &gz);

    // カンマ区切り文字列作成
    // snprintf関数でより安全に
    char msg[MSGBUFFER_LENGTH + 1]; 
    auto written = snprintf(msg, sizeof(msg), "%.3f,%.3f,%.3f,%.3f,%.3f,%.3f", ax, ay, az, gx, gy, gz);
    if(written == sizeof(msg)) {
      sendError = true;
    }

    // ESP-NOW送信
    esp_now_send(targetAddress, (uint8_t *) msg, strlen(msg));

    // 送信中の表示、適当に間引く
    if(sendCount % 0x10 == 0) {
      M5.Lcd.fillScreen(!sendError ? BLACK : RED);
      M5.Lcd.setCursor(0, 20);
      M5.Lcd.printf("RECORDING...\n%s", msg);
    }

    // 送信回数のインクリメント
    ++ sendCount;
  } else {
    // 停止中の表示
    M5.Lcd.fillScreen(BLACK);
    M5.Lcd.setCursor(0, 20);
    M5.Lcd.println("STOPPED\nPress Btn A to Start");
  }

  delay(10); // 100Hz
}
