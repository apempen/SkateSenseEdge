#include <Arduino.h>
#include <M5StickCPlus2.h>
#include <esp_now.h>
#include <WiFi.h>


volatile uint16_t receiveCount = 0;


// 受信時に呼ばれる関数
void OnDataRecv(const esp_now_recv_info* info, const uint8_t *incomingData, int len) {
    // 1. シリアルに出力
    Serial.write(incomingData, len);
    Serial.println();

	// 受信カウントをインクリメント
	auto tmp = receiveCount;
	receiveCount = tmp + 1;
}

void setup() {
    auto cfg = M5.config();
    StickCP2.begin(cfg);
    Serial.begin(115200);
    setCpuFrequencyMhz(80); // 省電力化 https://msr-r.net/m5stickc-mobilebattery/
    StickCP2.Display.setBrightness(4); // 省電力化

    // 画面の初期設定
    StickCP2.Display.setRotation(1);
    StickCP2.Display.setTextColor(GREEN);
    StickCP2.Display.setFont(&fonts::FreeSansBold9pt7b);
    StickCP2.Display.drawString("RX READY", StickCP2.Display.width() / 2, StickCP2.Display.height() / 2 - 10);

    // 通信の初期設定
    WiFi.mode(WIFI_STA);
    WiFi.disconnect();

    if (esp_now_init() != ESP_OK) {
        StickCP2.Display.fillScreen(RED);
        StickCP2.Display.drawString("Init Failed", StickCP2.Display.width() / 2, StickCP2.Display.height() / 2);
        return;
    }

    esp_now_register_recv_cb(OnDataRecv);
}

void loop() {
    // ESP-NOWはイベント駆動なのでloop内は空でも動作します

    // 3. 画面を更新
    StickCP2.Display.fillScreen(BLACK); // 画面をクリア
	StickCP2.Display.setCursor(0, 20);
	StickCP2.Display.printf("Recv cnt: %d", receiveCount);
    delay(1000 / 10);  // 更新は10Hz程度で
}
