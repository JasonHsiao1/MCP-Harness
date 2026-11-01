#include <Arduino.h>
#include <Wire.h>
#include <SPI.h>

// ==============================================================================
// Pin Assignments (AI-Deck Multi-Bus Configuration)
// ==============================================================================
// I2C Master
#define PIN_I2C_SDA  8   // Connected to Pico GP16 & MCP4725 SDA
#define PIN_I2C_SCL  9   // Connected to Pico GP17 & MCP4725 SCL

// SPI Master
#define PIN_SPI_SCK  12  // Connected to Pico GP2
#define PIN_SPI_CS   10  // Connected to Pico GP1
#define PIN_SPI_MOSI 11  // Connected to Pico GP0
#define PIN_SPI_MISO 13  // Connected to Pico GP3

// UART0 Cross-Connection
#define PIN_UART_TX  43  // ESP32 U0TXD -> Pico GP5 (UART1 RX)
#define PIN_UART_RX  44  // ESP32 U0RXD <- Pico GP4 (UART1 TX)

#define NEOPIXEL_PIN 38

// SparkFun MCP4725 I2C Address
#define MCP4725_ADDR 0x60

static const uint16_t DAC_STEPS[] = { 620, 1489, 2482, 3723 };
static const float VOLT_STEPS[]    = { 0.50f, 1.20f, 2.00f, 3.00f };
static const int NUM_STEPS = 4;

static uint32_t step_index = 0;
static SPIClass spi_bus(FSPI);
static HardwareSerial SerialUART(1);

void setup() {
    Serial.begin(115200); // Native USB CDC Serial
    delay(1000);

    rgbLedWrite(NEOPIXEL_PIN, 0, 0, 0);

    Serial.println("\n========================================================");
    Serial.println("   AI-Deck Multi-Bus Test (I2C + SPI + UART0)          ");
    Serial.println("========================================================");
    Serial.printf ("  I2C Master : SDA=GPIO%d, SCL=GPIO%d\n", PIN_I2C_SDA, PIN_I2C_SCL);
    Serial.printf ("  SPI Master : SCK=GPIO%d, CS=GPIO%d, MOSI=GPIO%d\n",
                   PIN_SPI_SCK, PIN_SPI_CS, PIN_SPI_MOSI);
    Serial.printf ("  UART Master: TX=GPIO%d -> Pico GP5, RX=GPIO%d <- Pico GP4\n",
                   PIN_UART_TX, PIN_UART_RX);
    Serial.println("========================================================\n");

    // 1. Initialize I2C Master
    Wire.setPins(PIN_I2C_SDA, PIN_I2C_SCL);
    Wire.begin();
    Wire.setClock(100000);

    // 2. Initialize SPI Master
    pinMode(PIN_SPI_CS, OUTPUT);
    digitalWrite(PIN_SPI_CS, HIGH);
    spi_bus.begin(PIN_SPI_SCK, PIN_SPI_MISO, PIN_SPI_MOSI, PIN_SPI_CS);

    // 3. Initialize Hardware UART0 on GPIO 43/44
    SerialUART.begin(115200, SERIAL_8N1, PIN_UART_RX, PIN_UART_TX);

    // Verify MCP4725 presence
    Wire.beginTransmission(MCP4725_ADDR);
    if (Wire.endTransmission() == 0) {
        Serial.printf("[I2C SCAN] SUCCESS: MCP4725 ACKed at 0x%02X!\n", MCP4725_ADDR);
        rgbLedWrite(NEOPIXEL_PIN, 0, 80, 0);
    }
    delay(300);
    rgbLedWrite(NEOPIXEL_PIN, 0, 0, 0);
}

void loop() {
    int current_step = step_index % NUM_STEPS;
    uint16_t dac_code = DAC_STEPS[current_step];
    float target_volts = VOLT_STEPS[current_step];
    step_index++;

    // 1. I2C DAC Write
    uint8_t hi_byte = (uint8_t)((dac_code >> 8) & 0x0F);
    uint8_t lo_byte = (uint8_t)(dac_code & 0xFF);
    Wire.beginTransmission(MCP4725_ADDR);
    Wire.write(hi_byte);
    Wire.write(lo_byte);
    uint8_t i2c_err = Wire.endTransmission();

    Serial.printf("\n[STEP #%u] DAC Target: %.2f V | I2C ACK: %s\n",
                  step_index, target_volts, (i2c_err == 0) ? "YES" : "NACK");

    // 2. SPI Burst
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

    // 3. UART Transmission to Pico GP5
    SerialUART.printf("ESP32_STEP_%u\n", step_index);
    Serial.printf("[UART TX] Sent 'ESP32_STEP_%u' via GPIO 43 -> Pico GP5\n", step_index);

    // 4. Check for UART Echo from Pico GP4
    delay(50);
    while (SerialUART.available()) {
        String echo = SerialUART.readStringUntil('\n');
        Serial.printf("[UART RX ECHO] Recv from Pico GP4 -> GPIO 44: %s\n", echo.c_str());
    }

    rgbLedWrite(NEOPIXEL_PIN, 0, 0, 80);
    delay(100);
    rgbLedWrite(NEOPIXEL_PIN, 0, 0, 0);

    delay(1200);
}
