# shopifyPi

# Shopify Order Display on Raspberry Pi OLED

This project runs on a **Raspberry Pi** and listens for **Shopify order webhooks** to display order details on an **SH1106 OLED screen**. It also **flashes an LED** when a new order arrives and plays an optional sound.

## ✨ Features
- 📦 **Displays new Shopify orders** on an OLED screen.
- 🌩️ **Lightning animation** before showing order details.
- 🚀 **Smooth scrolling** for long product names.
- 🔄 **Cycles through order details** before returning to idle.
- 🔔 **Flashing LED** on order arrival.

## 🛠️ Requirements

- Raspberry Pi (Zero 2W, 3, 4, etc.)
- SH1106 or SSD1306 OLED display (I2C)
- Python 3.x
- **Shopify webhook** integration
- (Optional) Speaker for **audio alerts**

## 📦 Installation

### 1️⃣ **Clone the Repository**
```bash
git clone https://github.com/your-repo/shopifyPi.git
cd shopify-oled-display
```

### 2️⃣**Install Dependancies**
```bash
pip3 install -r requirements.txt
```

### 3️⃣ Enable I2C on Raspberry Pi (if not already)
```bash
sudo raspi-config
```
 - Navigate to Interfacing Options > I2C > Enable
 - Save and exit
 - Check if OLED is detected
```bash
sudo i2cdetect -y 1
```
 - It should show `0x3C` or similar

 ### 4️⃣ Setup Your Shopify Webhook
 - Create a .env in the root and save these:
   - `SHOPIFY_API_KEY=xxx`
   - `SHOPIFY_API_SECRET=xxx`
   - `SHOPIFY_STORE_NAME=example.myshopify.com`
 - Go to your Shopify admin panel
 - Navigate to Settings > API > Webhooks
 - Create a new webhook with the following settings:
 - Topic: `orders`
 - Address: `http://your-raspberry-pi-ip:5000/webhook`
 - Format: `json`
 - Save and test the webhook

### 5️⃣ Run the Application
```bash
python3 mainApp.py
```
- The console will show an Ngrok public URL (eg. `https://xyz.ngrok.io/webhook/order`) <- This is what you will use in the step above

### 🎛️ Configuration
You can modify:

 - DISPLAY_WIDTH & DISPLAY_HEIGHT for different screen sizes.
 - SCROLL_SPEED to adjust text scrolling speed.
 - LED Pin (default is GPIO 17).

 ### General Wiring for Pi 4 B and Oled Displays (.91in and .96in using sh1106 and ssd1306)

|Component	|Raspberry Pi Pin|
|-----------|----------------|
|**OLED VCC**	|3.3V (Pin 1)    |
|**OLED GND**	|GND (Pin 9)     |
|**OLED SDA**	|GPIO 2 (Pin 3)  |
|**OLED SCL**	|GPIO 3 (Pin 5)  |
|**LED +**	    |GPIO 17 (Pin 11)|
|**LED -**	    |GND (Pin 9)     |

Built with ❤️ on Raspberry Pi!