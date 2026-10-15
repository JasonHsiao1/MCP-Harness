#include <Arduino.h>

// Onboard WS2812 / NeoPixel LED on ESP32-S3-DevKitC-1
#define NEOPIXEL_PIN 38

// External Pushbutton connected to GPIO 4 (Pull-Down configuration)
// Circuit:
//   - 10k resistor from GPIO 4 to GND (Pull-Down)
//   - Pushbutton from GPIO 4 to 3.3V (VCC)
// Logic:
//   - Unpressed: LOW  (0V)
//   - Pressed:   HIGH (3.3V)
#define BUTTON_PIN 4

// Rainbow colors for the NeoPixel
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
static uint32_t step_count = 0;

void setup() {
    Serial.begin(115200);
    delay(1000);

    // Configure GPIO 4 for Pull-Down input
    pinMode(BUTTON_PIN, INPUT_PULLDOWN);

    // Clear NeoPixel to OFF
    rgbLedWrite(NEOPIXEL_PIN, 0, 0, 0);

    Serial.println("\n========================================================");
    Serial.println("  AI-Deck ESP32-S3: GPIO 4 Pull-Down Button Blink Demo  ");
    Serial.println("========================================================");
    Serial.printf ("* NeoPixel Pin: GPIO %d\n", NEOPIXEL_PIN);
    Serial.printf ("* Button Pin:   GPIO %d (Pull-Down: Unpressed=LOW, Pressed=HIGH)\n", BUTTON_PIN);
    Serial.println("--------------------------------------------------------");
    Serial.println("Hold or press button to cycle rainbow colors on NeoPixel.");
    Serial.println("Release button to turn LED off.");
    Serial.println("========================================================\n");
}

void loop() {
    int button_state = digitalRead(BUTTON_PIN);

    if (button_state == HIGH) {
        // Button is pressed (3.3V connected to GPIO 4)
        step_count++;
        const Color &c = RAINBOW[color_idx];

        Serial.printf("[BUTTON PRESSED (HIGH)] Step #%u | %s -> R:%d, G:%d, B:%d\n", 
                      step_count, c.name, c.r, c.g, c.b);

        // Display current rainbow color
        rgbLedWrite(NEOPIXEL_PIN, c.r, c.g, c.b);
        delay(350);

        // Advance to next color
        color_idx = (color_idx + 1) % NUM_COLORS;
    } else {
        // Button is released (Pulled down to GND)
        rgbLedWrite(NEOPIXEL_PIN, 0, 0, 0);

        static uint32_t idle_ticks = 0;
        idle_ticks++;
        if (idle_ticks % 10 == 0) {
            Serial.println("[IDLE] GPIO 4 is LOW. Waiting for button press (3.3V)...");
        }
        delay(150);
    }
}
