#include <Arduino.h>

// Onboard WS2812 / NeoPixel LED on ESP32-S3-DevKitC-1
#define NEOPIXEL_PIN 38

// Rainbow colors (scaled to comfortable bench brightness)
struct Color {
    const char *name;
    uint8_t r;
    uint8_t g;
    uint8_t b;
};

const Color RAINBOW[] = {
    {"Red",     60,   0,   0},
    {"Orange",  60,  25,   0},
    {"Yellow",  50,  50,   0},
    {"Green",    0,  60,   0},
    {"Cyan",     0,  50,  50},
    {"Blue",     0,   0,  60},
    {"Indigo",  25,   0,  50},
    {"Violet",  50,   0,  45}
};

const size_t NUM_COLORS = sizeof(RAINBOW) / sizeof(RAINBOW[0]);
static size_t color_idx = 0;
static uint32_t cycle_count = 0;

void setup() {
    Serial.begin(115200);
    delay(1000);

    // Initialize NeoPixel to OFF
    rgbLedWrite(NEOPIXEL_PIN, 0, 0, 0);

    Serial.println("\n===========================================");
    Serial.println("  AI-Deck ESP32-S3 Continuous Rainbow Demo ");
    Serial.printf ("  Driving WS2812 on GPIO %d               \n", NEOPIXEL_PIN);
    Serial.println("===========================================");
}

void loop() {
    const Color &c = RAINBOW[color_idx];
    Serial.printf("[NEOPIXEL] Cycle %u | %s -> R:%d, G:%d, B:%d\n", 
                  cycle_count, c.name, c.r, c.g, c.b);

    rgbLedWrite(NEOPIXEL_PIN, c.r, c.g, c.b);
    delay(500);

    color_idx = (color_idx + 1) % NUM_COLORS;
    if (color_idx == 0) {
        cycle_count++;
    }
}
