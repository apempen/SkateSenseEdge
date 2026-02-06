#include <M5StickCPlus.h>

void setup() {
  M5.begin();

  Serial.begin(115200);
  delay(500);
  Serial.print("replaced at issure/4\n");

  pinMode(10, OUTPUT);
}

void loop() {
  // put your main code here, to run repeatedly:
  digitalWrite(10, HIGH); // turn the LED on (HIGH is the voltage level)
  Serial.print("LED TURN ON\n");
  delay(1000); // wait for a second
  digitalWrite(10, LOW); // turn the LED off by making the voltage LOW
  Serial.print("LED TURN OFF\n");
  delay(1000); // wait for a second
}
