#include <Arduino.h>
#include <Wire.h>
#include <SPI.h>

// ==============================================================================
// Pin Assignments (AI-Deck Test Configuration)
// ==============================================================================
#define PIN_I2C_SDA  8   // Connected to Pico GP16 & MCP4725 SDA
#define PIN_I2C_SCL  9   // Connected to Pico GP17 & MCP4725 SCL

#define PIN_SPI_SCK  12  // Connected to Pico GP2
#define PIN_SPI_CS   10  // Connected to Pico GP1
#define PIN_SPI_MOSI 11  // Connected to Pico GP0
#define PIN_SPI_MISO 13  // Connected to Pico GP3

#define NEOPIXEL_PIN 38

// SparkFun MCP4725 I2C Address
#define MCP4725_ADDR 0x60

// 4-step test voltages: 0.5V, 1.2V, 2.0V, 3.0V (assuming 3.3V VDD)
static const uint16_t DAC_STEPS[] = { 620, 1489, 2482, 3723 };
static const float VOLT_STEPS[]    = { 0.50f, 1.20f, 2.00f, 3.00f };
static const int NUM_STEPS = 4;

static uint32_t step_index = 0;
static SPIClass spi_bus(FSPI);

void setup() {
    Serial.begin(115200);
    delay(1000);

    rgbLedWrite(NEOPIXEL_PIN, 0, 0, 0);

    Serial.println("\n========================================================");
    Serial.println("   AI-Deck Mixed-Signal: ESP32-S3 + MCP4725 DAC Master  ");
    Serial.println("========================================================");
    Serial.printf ("  I2C Master: SDA=GPIO%d, SCL=GPIO%d\n", PIN_I2C_SDA, PIN_I2C_SCL);
    Serial.printf ("  Target DAC : MCP4725 at I2C address 0x%02X\n", MCP4725_ADDR);
    Serial.printf ("  SPI Master: SCK=GPIO%d, CS=GPIO%d, MOSI=GPIO%d\n",
                   PIN_SPI_SCK, PIN_SPI_CS, PIN_SPI_MOSI);
    Serial.println("========================================================\n");

    // Initialize I2C Master
    Wire.setPins(PIN_I2C_SDA, PIN_I2C_SCL);
    Wire.begin();
    Wire.setClock(100000);

    // Initialize SPI Master
    pinMode(PIN_SPI_CS, OUTPUT);
    digitalWrite(PIN_SPI_CS, HIGH);
    spi_bus.begin(PIN_SPI_SCK, PIN_SPI_MISO, PIN_SPI_MOSI, PIN_SPI_CS);

    // I2C Bus Discovery
    Serial.println("[I2C SCAN] Checking for MCP4725...");
    Wire.beginTransmission(MCP4725_ADDR);
    uint8_t err = Wire.endTransmission();
    if (err == 0) {
        Serial.printf("[I2C SCAN] SUCCESS: MCP4725 ACKed at 0x%02X!\n", MCP4725_ADDR);
        rgbLedWrite(NEOPIXEL_PIN, 0, 80, 0); // Green
    } else {
        Serial.printf("[I2C SCAN] WARNING: Device at 0x%02X returned error: %d\n", MCP4725_ADDR, err);
        rgbLedWrite(NEOPIXEL_PIN, 80, 0, 0); // Red
    }
    delay(500);
    rgbLedWrite(NEOPIXEL_PIN, 0, 0, 0);
}

void loop() {
    int current_step = step_index % NUM_STEPS;
    uint16_t dac_code = DAC_STEPS[current_step];
    float target_volts = VOLT_STEPS[current_step];
    step_index++;

    // 1. Write DAC Code to MCP4725 (Fast Mode: 2 bytes)
    // Byte 1: [0 0 PD1 PD0 D11 D10 D9 D8] (PD=00 normal mode)
    // Byte 2: [D7 D6 D5 D4 D3 D2 D1 D0]
    uint8_t hi_byte = (uint8_t)((dac_code >> 8) & 0x0F);
    uint8_t lo_byte = (uint8_t)(dac_code & 0xFF);

    Wire.beginTransmission(MCP4725_ADDR);
    Wire.write(hi_byte);
    Wire.write(lo_byte);
    uint8_t i2c_err = Wire.endTransmission();

    Serial.printf("\n[STEP #%u] Target: %.2f V | DAC Code: 0x%03X (%u) | I2C ACK: %s\n",
                  step_index, target_volts, dac_code, dac_code,
                  (i2c_err == 0) ? "YES (SUCCESS)" : "NACK (FAIL)");

    // Visual: Blue during step update
    rgbLedWrite(NEOPIXEL_PIN, 0, 0, 80);

    // 2. Also send SPI burst
    uint8_t tx_buf[] = { 0xDE, 0xAD, (uint8_t)current_step, hi_byte, lo_byte };
    digitalWrite(PIN_SPI_CS, LOW);
    delayMicroseconds(10);
    spi_bus.beginTransaction(SPISettings(1000000, MSBFIRST, SPI_MODE0));
    for (int i = 0; i < 5; i++) {
        spi_bus.transfer(tx_buf[i]);
    }
    spi_bus.endTransaction();
    delayMicroseconds(10);
    digitalWrite(PIN_SPI_CS, HIGH);

    delay(200);
    rgbLedWrite(NEOPIXEL_PIN, 0, 0, 0);

    delay(1300); // Wait 1.5 seconds per step for ADC settling and verification
}
