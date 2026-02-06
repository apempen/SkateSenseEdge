#include <WiFi.h>
#include <esp_now.h>

// 1. 送信側と完全に一致させる構造体
typedef struct struct_message {
    float accX;
    float accY;
    float accZ;
    float gyroX;
    float gyroY;
    float gyroZ;
} struct_message;

// 受信データを格納するインスタンス
struct_message incomingData;

// 2. データを受信したときに実行されるコールバック関数
void OnDataRecv(const uint8_t * mac, const uint8_t *incomingPacket, int len) {
    memcpy(&incomingData, incomingPacket, sizeof(incomingData));
    
    // Python側で分解しやすいよう、カンマ区切りで出力
    Serial.print(incomingData.accX);  Serial.print(",");
    Serial.print(incomingData.accY);  Serial.print(",");
    Serial.print(incomingData.accZ);  Serial.print(",");
    Serial.print(incomingData.gyroX); Serial.print(",");
    Serial.print(incomingData.gyroY); Serial.print(",");
    Serial.println(incomingData.gyroZ); // 最後は改行
}

void setup() {
    Serial.begin(115200);

    // Wi-FiをStationモードに設定
    WiFi.mode(WIFI_STA);

    // ESP-NOWの初期化
    if (esp_now_init() != ESP_OK) {
        Serial.println("ESP-NOWの初期化に失敗しました");
        return;
    }

    // 受信コールバック関数の登録
    esp_now_register_recv_cb(esp_now_recv_cb_t(OnDataRecv));
}

void loop() {
    // 受信処理はコールバックで行われるため、loop内は空でもOK
    // 取得したデータを使って計算や制御を行う場合はここに記述
}