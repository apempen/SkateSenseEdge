#include <esp_now.h>
#include <WiFi.h>

typedef struct struct_message {
    float accX, accY, accZ;
    float gyroX, gyroY, gyroZ;
} struct_message;

struct_message incomingData;
volatile bool newDataAvailable = false; // volatileを付けて最適化を防ぐ

void OnDataRecv(const uint8_t *mac, const uint8_t *incomingPacket, int data_len) {
    if (data_len == sizeof(incomingData)) {
        memcpy(&incomingData, incomingPacket, data_len);
        newDataAvailable = true; 
    }
}

void setup() {

    Serial.begin(921600); 
    WiFi.mode(WIFI_STA);
    if (esp_now_init() != ESP_OK) return;

    esp_now_register_recv_cb(esp_now_recv_cb_t(OnDataRecv));
}

void loop() {
    // 2. データが届いたときだけ、最小限の回数でシリアル送信
    if (newDataAvailable) {
        // カンマ区切りで一気に送信（末尾に改行）
        Serial.printf("%.2f,%.2f,%.2f,%.2f,%.2f,%.2f\n", 
                      incomingData.accX, incomingData.accY, incomingData.accZ,
                      incomingData.gyroX, incomingData.gyroY, incomingData.gyroZ);
        newDataAvailable = false; 
    }
}