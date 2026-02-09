#include <Arduino.h>
#include <M5StickCPlus2.h>
#include <esp_now.h>
#include <WiFi.h>


void OnDataRecv(const uint8_t * mac, const uint8_t *incomingData, int len) {
    Serial.write(incomingData, len);

    Serial.println();
}

void setup() {
    // M5StickC Plus2 初期化
    auto cfg = M5.config();
    StickCP2.begin(cfg);

    // シリアル通信開始
    Serial.begin(115200);

    // StickCP2.Display.setRotation(1);
    // StickCP2.Display.setTextColor(GREEN);
    // StickCP2.Display.setTextDatum(middle_center);
    // StickCP2.Display.setFont(&fonts::FreeSansBold9pt7b);
    // StickCP2.Display.drawString("RX READY", StickCP2.Display.width() / 2, StickCP2.Display.height() / 2);

    WiFi.mode(WIFI_STA);
    WiFi.disconnect();

    if (esp_now_init() != ESP_OK) {
        Serial.println("ESP-NOW Init Failed");
        StickCP2.Display.fillScreen(RED);
        StickCP2.Display.drawString("Init Failed", StickCP2.Display.width() / 2, StickCP2.Display.height() / 2);
        return;
    }

    esp_now_register_recv_cb(OnDataRecv);
}

void loop() {
    delay(1000);
}