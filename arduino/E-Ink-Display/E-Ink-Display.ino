// TRMNL DIY Kit - Button Test Example

// Display size defines, used in headers
#define MAX_IMAGE_HEIGHT 480 /* TRMNL 7.5" display: 800x480*/
#define MAX_IMAGE_WIDTH 800  /* TRMNL 7.5" display: 800x480*/

#include <SPI.h>
#include <TFT_eSPI.h> // E-Ink display driver
#include <WiFi.h>
#include <HTTPClient.h>
#include <FS.h>
#include <LittleFS.h>
#include <PNGdec.h>

// Deep sleep
// https://wiki.seeedstudio.com/XIAO_ESP32S3_Consumption/
// https://randomnerdtutorials.com/esp32-deep-sleep-arduino-ide-wake-up-sources/
#define USEC_TO_SEC 1000000ULL /* Conversion factor for micro seconds to seconds */

// Define button pins
const int BUTTON_D1 = D1; // First user button
const int BUTTON_D2 = D2; // Second user button
const int BUTTON_D4 = D4; // Third user button

// Battery voltage sense
const int BATTERY_PIN = 1; // GPIO1 (A0) - BAT_ADC
const int ADC_EN_PIN = 6;  // GPIO6 (A5) - ADC_EN
const float CALIBRATION_FACTOR = 0.968;

// Display Params
const int TEXT_SZ = 1;
const unsigned int Y_START = 10;
const unsigned int Y_DELTA = 20;
unsigned int y_pos = Y_START;
unsigned int x_pos = 10;

// WiFi Network
const String HOSTNAME = "E-Ink Display";
const char *SSID = "Harriman-1";
const char *PASSWD = "3135Charlie04";

// Server
const String SERVER = "http://192.168.0.120:8123";
const String DEVICE = "home-office";

#define FORMAT_LITTLEFS_IF_FAILED true

// Instantiate display driver object
EPaper epaper = EPaper();

// Serial status aware printing
void s_println(String msg)
{
    if (!Serial)
    {
        return;
    }
    Serial.println(msg);
}

void s_print(String msg)
{
    if (!Serial)
    {
        return;
    }
    Serial.print(msg);
}

void setup()
{
    // Initialize serial communication
    Serial.begin(115200);

    // Wait for the serial port to connect for up to 5 seconds
    unsigned long timeout = millis();
    while (!Serial && millis() - timeout < 1000)
    {
        delay(10);
    }

    s_println("TRMNL DIY Kit");

    // Configure button pins as inputs with internal pull-up resistors
    pinMode(BUTTON_D1, INPUT_PULLUP);
    pinMode(BUTTON_D2, INPUT_PULLUP);
    pinMode(BUTTON_D4, INPUT_PULLUP);

    // Configure ADC_EN
    pinMode(ADC_EN_PIN, OUTPUT);
    digitalWrite(ADC_EN_PIN, LOW); // Start with ADC disabled to save power

    // Configure ADC
    analogReadResolution(12);
    analogSetPinAttenuation(BATTERY_PIN, ADC_11db);

    // Configure display
    epaper.begin();
    epaper.setRotation(1); // Landscape
    // epaper.fillScreen(TFT_WHITE);
    epaper.setTextColor(TFT_BLACK, TFT_WHITE);
    epaper.setTextSize(TEXT_SZ);

    // Start file system
    if (!LittleFS.begin(true, "/littlefs"))
    {
        s_println("Failed to mount LittleFS");
    }
    else
    {
        s_println("LittleFS mounted successfully");
    }

    // WiFi Connect
    s_print("Connecting WiFi: ");
    s_println(String(SSID));

    WiFi.setHostname(HOSTNAME.c_str());
    WiFi.mode(WIFI_STA);
    WiFi.disconnect();
    WiFi.begin(SSID, PASSWD);
    while (WiFi.status() != WL_CONNECTED)
    {
        delay(250);
        s_print(".");
    }
    s_println("");
    s_print("connected, IP: ");
    s_println(String(WiFi.localIP()));

    // String ip_str = String("Connected - IP:");
    // ip_str.concat(WiFi.localIP().toString());
    // epaper.drawString(ip_str, x_pos, y_pos);
    // y_pos += Y_DELTA;
    // epaper.update();
}

float readBatteryVoltage()
{
    uint8_t n_samples = 8;
    // Enable ADC
    digitalWrite(ADC_EN_PIN, HIGH);
    delay(10); // Short delay to stabilize

    // Read 30 times and average for more stable readings
    long sum = 0;
    for (int i = 0; i < n_samples; i++)
    {
        sum += analogRead(BATTERY_PIN);
        delayMicroseconds(100);
    }

    // Disable ADC to save power
    digitalWrite(ADC_EN_PIN, LOW);

    // Calculate voltage
    float adc_avg = sum / (float)n_samples;
    float voltage = (adc_avg / 4095.0) * 3.6 * 2.0 * CALIBRATION_FACTOR;

    return voltage;
}

// Converts battery voltage value to string.
String batteryVoltageToString(float bat_v)
{
    // Convert to string
    if (bat_v >= 4.0)
    {
        return "Full";
    }
    else if (bat_v >= 3.7)
    {
        return "Good";
    }
    else if (bat_v >= 3.5)
    {
        return "Medium";
    }
    else if (bat_v >= 3.2)
    {
        return "Low";
    }
    return "Critical";
}

// Reads status & returns a status string
String readBatteryStatus()
{
    float bat_v = readBatteryVoltage();
    return batteryVoltageToString(bat_v);
}

String service_url_get(String api)
{
    String url = String(SERVER);
    url.concat("/");
    url.concat(api);
    url.concat("/");
    url.concat(DEVICE);
    return url;
}

// service_data_get
// Retrieves data from the server for the given service.
// Device name is passed by default as defined by service_url_get().
//
// Params:
//   service - Name of service endpoint from which to request data.
//   data:
//     - If empty string, data will be returned in this variable.
//     - If non-empty, data will be written to file system with given file name.
int service_data_get(String service, String &data)
{
    // Connected?
    int conn_status = WiFi.status();
    if (conn_status != WL_CONNECTED)
    {
        if (Serial)
        {
            Serial.printf("WiFi not connected, status: %d\n", conn_status);
        }
        return conn_status;
    }

    // URL for service for this device
    String url = service_url_get(service);
    if (Serial)
    {
        Serial.printf("Service URL: %s\n", url.c_str());
    }
    delay(10);

    // Request data
    HTTPClient http;
    http.begin(url);
    int httpCode = http.GET();
    if (httpCode != HTTP_CODE_OK)
    {
        http.end();
        return httpCode;
    }

    // Open file if requested.
    bool use_file = data.length() > 0;
    fs::File file = fs::File();
    if (use_file)
    {
        s_println("Opening file for write: " + data);
        file = LittleFS.open(data.c_str(), "w");

        if (!file)
        {
            s_println("Failed to open file for writing");
            http.end();
            return -1;
        }
    }

    // Read data stream.
    WiFiClient *stream = http.getStreamPtr();
    int len = http.getSize();
    uint8_t buf[128] = {0};

    uint32_t total_read = 0;
    while (http.connected() && (len > 0 || len == -1))
    {
        size_t size = stream->available();
        if (size)
        {
            // Read bytes into the buffer
            int c = stream->readBytes(buf, ((size > sizeof(buf)) ? sizeof(buf) : size));
            total_read += c;
            s_println("   bytes read: " + String(total_read));
            if (use_file)
            {
                file.write(buf, c);
            }
            else
            {
                // Store into output reference
                String buf_str = (char *)buf;
                data.concat(buf_str);
            }

            if (len > 0)
            {
                len -= c;
            }
        }
    }

    if (use_file)
    {
        file.close();
        s_println("File write complete");
    }

    http.end();
    return httpCode;
}

void device_state_post()
{
    // Connected?
    int conn_status = WiFi.status();
    if (conn_status != WL_CONNECTED)
    {
        if (Serial)
        {
            Serial.printf("WiFi not connected, status: %d\n", conn_status);
        }
        return;
    }

    // URL for service for this device
    String url = String(SERVER);
    url.concat("/state");
    if (Serial)
    {
        Serial.printf("Status URL: %s\n", url.c_str());
    }
    delay(10);

    // Prepare JSON payload
    String payload = String("{");
    payload.concat("\"device\":\"");
    payload.concat(DEVICE);
    payload.concat("\",");

    payload.concat("\"battery_voltage\": \"");
    float bat_v = readBatteryVoltage();
    payload.concat(String(bat_v, 2));
    payload.concat("\"");

    payload.concat("}");

    // Post data
    HTTPClient http;
    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    s_println("Posting status: " + payload);
    int httpCode = http.POST(payload);
    if (httpCode != HTTP_CODE_OK)
    {
        if (Serial)
        {
            Serial.printf("Status post error: %d\n", httpCode);
        }
    }
    else
    {
        s_println("Status posted successfully");
    }
    http.end();
}

// Open the PNG file from LittleFS
PNG png;
fs::File _png_file;
void *png_open(const char *filename, int32_t *size)
{
    _png_file = LittleFS.open(filename, "r");
    if (!_png_file)
    {
        s_println("Failed to open PNG file");
        return nullptr;
    }
    *size = _png_file.size();
    return &_png_file;
}

void png_close(void *handle)
{
    fs::File pngfile = *((fs::File *)handle);
    if (pngfile)
        pngfile.close();
}

int32_t png_read(PNGFILE *page, uint8_t *buffer, int32_t length)
{
    if (!_png_file)
        return 0;
    page = page; // Avoid warning
    return _png_file.read(buffer, length);
}

int32_t png_seek(PNGFILE *page, int32_t position)
{
    if (!_png_file)
        return 0;
    page = page; // Avoid warning
    return _png_file.seek(position);
}

// Draw callback for PNGdec
// This next function will be called during decoding of the png file to
// render each image line to the TFT.  If you use a different TFT library
// you will need to adapt this function to suit.
// Callback function to draw pixels to the display
int png_draw(PNGDRAW *pDraw)
{
    uint16_t lineBuffer[MAX_IMAGE_WIDTH];
    png.getLineAsRGB565(pDraw, lineBuffer, PNG_RGB565_BIG_ENDIAN, 0xffffffff); // No background

    // Draw row
    for (uint32_t i = 0; i < png.getWidth(); i++)
    {
        epaper.drawPixel(i, pDraw->y, lineBuffer[i]);
    }
    return png.getWidth();
}

void screen_clear()
{
    // Clear screen
    epaper.fillScreen(TFT_WHITE);
    epaper.update();
    y_pos = Y_START;
}

void image_read_and_display()
{
    device_state_post();

    // Download file
    String filename = "/image.png";
    int resp = service_data_get(String("image"), filename);

    if (resp != HTTP_CODE_OK)
    {
        if (Serial)
        {

            Serial.printf("Network read error: %d\n", resp);
        }
        epaper.drawString("Network Read Error", x_pos, y_pos);
        y_pos += Y_DELTA;
    }
    else
    {
        epaper.drawString("File downloaded", x_pos, y_pos);
        y_pos += Y_DELTA;

        uint32_t err = png.open(filename.c_str(), png_open, png_close, png_read, png_seek, png_draw);
        if (err != PNG_SUCCESS)
        {
            if (Serial)
            {

                Serial.printf("PNG open error: %d\n", err);
            }
            epaper.drawString("PNG Open Error", x_pos, y_pos);
            y_pos += Y_DELTA;
            return;
        }

        if (png.getWidth() > MAX_IMAGE_WIDTH)
        {
            s_println("PNG image too wide for display");
            epaper.drawString("PNG Too Wide", x_pos, y_pos);
            y_pos += Y_DELTA;
            png.close();
            return;
        }

        if (Serial)
        {
            Serial.printf("image info: (%d x %d), %d bpp, pixel type: %d\n",
                          png.getWidth(),
                          png.getHeight(),
                          png.getBpp(),
                          png.getPixelType());
        }

        // Decode the PNG file
        err = png.decode(nullptr, 0);
        if (err != PNG_SUCCESS)
        {
            if (Serial)
            {

                Serial.printf("PNG decode error: %d\n", err);
            }
            epaper.drawString("PNG Decode Error", x_pos, y_pos);
            y_pos += Y_DELTA;
            png.close();
            return;
        }
        y_pos += png.getHeight();

        // Update display
        epaper.update();

        // Close the file
        png.close();

    } // HTTP Response OK

    // Read the time to sleep until next update
    String payload = String();
    resp = service_data_get(String("delay"), payload);
    if (resp != HTTP_CODE_OK)
    {
        if (Serial)
        {
            Serial.printf("Network read error: %d\n", resp);
        }
        epaper.drawString("Network Read Error", x_pos, y_pos);
        y_pos += Y_DELTA;
    }
    else
    {
        s_println("Sleep delay: " + payload + " [sec]");

        // Program wake timer & go to sleep
        int sleep_secs = payload.toInt();
        esp_sleep_enable_timer_wakeup(sleep_secs * USEC_TO_SEC);
        esp_deep_sleep_start();
    }
}

void loop()
{
    // Read button states (buttons are LOW when pressed because of pull-up resistors)
    bool d1Pressed = !digitalRead(BUTTON_D1);
    bool d2Pressed = !digitalRead(BUTTON_D2);
    bool d4Pressed = !digitalRead(BUTTON_D4);

    // Print button states if any button is pressed
    if (d1Pressed)
    {
        screen_clear();
        String status_str = readBatteryStatus();
        if (Serial)
        {
            Serial.printf("Battery: %s", status_str);
        }
        s_println(String());

        // Write to screen
        String disp_str = String("Battery: ");
        disp_str.concat(status_str);
        float v_bat = readBatteryVoltage();
        String v_str = String(v_bat, 2);
        disp_str.concat(" (");
        disp_str.concat(v_str);
        disp_str.concat("V)");

        epaper.drawString(disp_str, x_pos, y_pos);
        epaper.update();
        y_pos += Y_DELTA;

        // Add a small delay to avoid repeated readings
        delay(200);
    }
    else if (d2Pressed)
    {
        image_read_and_display();

        // Add a small delay to avoid repeated readings
        delay(200);
    }
    else if (d4Pressed)
    {
        s_println("Button 4 pressed");

        String payload = String();
        int resp = service_data_get(String("json"), payload);

        if (resp != HTTP_CODE_OK)
        {
            if (Serial)
            {
                Serial.printf("Network read error: %d\n", resp);
            }
            epaper.drawString("Network Read Error", x_pos, y_pos);
            y_pos += Y_DELTA;
            delay(200);
        }
        else
        {
            String msg = String("Server Reponse: ");
            msg.concat(payload);
            epaper.drawString(msg, x_pos, y_pos);
            epaper.update();
            y_pos += Y_DELTA;
        }
        // Add a small delay to avoid repeated readings
        delay(200);
    }

    // Read the calendar
    image_read_and_display();
}