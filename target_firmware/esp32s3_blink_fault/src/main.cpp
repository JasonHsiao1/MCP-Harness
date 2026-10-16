#include <Arduino.h>

// Onboard WS2812 / NeoPixel LED on ESP32-S3-DevKitC-1
#define NEOPIXEL_PIN 38

static uint32_t blink_count = 0;

void setup() {
    Serial.begin(115200);
    delay(1000);

    // Initialize NeoPixel to OFF
    rgbLedWrite(NEOPIXEL_PIN, 0, 0, 0);

    Serial.println("\n===========================================");
    Serial.println("   AI-Deck ESP32-S3: Green Blink           ");
    Serial.printf ("   Driving WS2812 on GPIO %d              \n", NEOPIXEL_PIN);
    Serial.println("===========================================");
}

void loop() {
    blink_count++;

    // Green ON (R:0, G:80, B:0)
    Serial.printf("[NEOPIXEL] Blink #%u | GREEN -> R:0, G:80, B:0\n", blink_count);
    rgbLedWrite(NEOPIXEL_PIN, 0, 80, 0);
    delay(500);

    // OFF
    Serial.printf("[NEOPIXEL] Blink #%u | OFF -> R:0, G:0, B:0\n", blink_count);
    rgbLedWrite(NEOPIXEL_PIN, 0, 0, 0);
    delay(500);
}