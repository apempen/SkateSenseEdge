#include <M5StickCPlus2.h>
#include <esp_now.h>
#include <WiFi.h>

// 受信機のMACアドレス
uint8_t targetAddress[] = {0x4c, 0xc3, 0x82, 0x9b, 0xab, 0x34}; 

// 送信管理
bool isSending = true;
uint32_t sendCount = 0;
char msgBuffer[128]; // IMUデータ用なら128あれば十分です

void setup() {
  // M5.begin() で IMU も初期化されます
  auto cfg = M5.config();
  M5.begin(cfg);

  // 省電力設定
  setCpuFrequencyMhz(80);
  M5.Display.setBrightness(4);
  
  M5.Display.setRotation(1);
  M5.Display.setTextColor(GREEN);
  M5.Display.setFont(&fonts::FreeSansBold9pt7b);

  // ESP-NOW 初期化
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();

  if (esp_now_init() != ESP_OK) {
    M5.Display.println("ESP-NOW Init Failed");
    return;
  }

  esp_now_peer_info_t peerInfo = {};
  memcpy(peerInfo.peer_addr, targetAddress, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;

  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    M5.Display.println("Failed to add peer");
    return;
  }

  M5.Display.fillScreen(BLACK);
  M5.Display.println("READY");
}

void loop() {
  M5.update();

  if (isSending) {
    // 1. IMUデータの取得（必ず 0.0f で初期化してゴミデータを防ぐ）
    float ax=0, ay=0, az=0, gx=0, gy=0, gz=0;
    
    // Plus2 の推奨手順：updateを呼んでから取得
    M5.Imu.update(); 
    M5.Imu.getAccelData(&ax, &ay, &az);
    M5.Imu.getGyroData(&gx, &gy, &gz);

    // 2. カンマ区切り文字列の作成
    // 文字列の終端を保証し、バッファオーバーフローを防ぐ
    int len = snprintf(msgBuffer, sizeof(msgBuffer), "%.3f,%.3f,%.3f,%.3f,%.3f,%.3f", 
                       ax, ay, az, gx, gy, gz);

    // 3. ESP-NOW送信
    if (len > 0) {
      esp_now_send(targetAddress, (uint8_t *)msgBuffer, len);
    }

    // 4. 画面表示（描画負荷を抑えるため10回に1回）
    if (sendCount % 10 == 0) {
      M5.Display.fillScreen(BLACK);
      M5.Display.setCursor(0, 20);
      M5.Display.printf("%.2f,%.2f,%.2f,%.2f,%.2f,%.2f\nCnt: %d", ax,ay,az,gx,gy,gz, sendCount);
    }

    sendCount++;
  }

  delay(10); // 100Hz
}