import os
import random
import time
import threading

from flask import Flask, request
from pyngrok import ngrok
from dotenv import load_dotenv

# GPIO
import RPi.GPIO as GPIO

# Luma.OLED + PIL
from luma.core.interface.serial import i2c
from luma.oled.device import sh1106
from luma.core.render import canvas
from PIL import ImageFont

# Optional Audio
# import pygame


# ==========================
# 1. LED Manager
# ==========================
class LEDManager:
    """
    Manages an LED on a specific GPIO pin.
    Allows blinking or simple on/off control.
    """
    def __init__(self, gpio_pin=17):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(gpio_pin, GPIO.OUT)
        self.gpio_pin = gpio_pin
        # Start with LED off
        GPIO.output(self.gpio_pin, GPIO.LOW)

    def blink(self, times=5, on_time=0.2, off_time=0.2):
        """
        Blink the LED a certain number of times.
        """
        for _ in range(times):
            GPIO.output(self.gpio_pin, GPIO.HIGH)
            time.sleep(on_time)
            GPIO.output(self.gpio_pin, GPIO.LOW)
            time.sleep(off_time)

    def turn_on(self):
        GPIO.output(self.gpio_pin, GPIO.HIGH)

    def turn_off(self):
        GPIO.output(self.gpio_pin, GPIO.LOW)

    def cleanup(self):
        """
        Release GPIO resources.
        Call this at program exit.
        """
        GPIO.cleanup()


# ==========================
# 2. Display Manager
# ==========================
class DisplayManager:
    """
    Manages the SH1106 OLED display, states, and animations.
    Runs in a thread (display_loop) to continuously update the screen.
    """

    # Possible states
    CELEBRATION = 1
    ORDER_INFO  = 2
    IDLE        = 3

    def __init__(self, width=128, height=64, rotate=0, font_path="DejaVuSans.ttf"):
        # Initialize Luma.OLED
        serial = i2c(port=1, address=0x3C)
        self.device = sh1106(serial, width=width, height=height, rotate=rotate)

        # Try loading a TTF font
        try:
            self.font = ImageFont.truetype(font_path, 12)
        except:
            self.font = ImageFont.load_default()

        # Display State Variables
        self.display_state   = self.IDLE
        self.state_start_time = time.time()
        self.scroll_position = 0

        # Order Screens
        self.screens = []
        self.screen_index    = 0
        self.cycles_remaining = 0
        self.order_data      = None

        # Thread control
        self.running = True

    def start(self):
        """
        Start the display loop in a background thread.
        """
        threading.Thread(target=self.display_loop, daemon=True).start()

    def stop(self):
        """
        Stop the display loop.
        """
        self.running = False

    def display_loop(self):
        """
        Continuously updates the display based on the current state.
        """
        while self.running:
            with canvas(self.device) as draw:
                if self.display_state == self.CELEBRATION:
                    self._show_celebration_screen(draw)
                    # After 3s, switch to ORDER_INFO
                    if time.time() - self.state_start_time > 3: # Change this to set celebration duration
                        self.display_state = self.ORDER_INFO
                        self.state_start_time = time.time()
                        self.screen_index = 0
                        self.cycles_remaining = 2  # e.g., show screens 2 cycles

                elif self.display_state == self.ORDER_INFO:
                    if self.screens:
                        max_width = len(self.screens[self.screen_index])
                        scroll_limit = max_width + self.device.width + 156

                        # If screen_index > 1 => SCROLL this screen
                        if self.screen_index > 1:
                            self._draw_multiline_centered(draw, self.screens[self.screen_index], self.scroll_position)
                            # Increment scroll position
                            self.scroll_position = (self.scroll_position + 10) % scroll_limit
                        else:
                            # For screens 0 & 1, do no scrolling (offset=0)
                            self._draw_multiline_centered(draw, self.screens[self.screen_index], 0)

                        # Time-based and width based screen switching
                        if time.time() - self.state_start_time > 8 or self.scroll_position >= scroll_limit + max_width:
                            self.screen_index += 1
                            self.scroll_position = 0
                            self.state_start_time = time.time()
                            if self.screen_index >= len(self.screens):
                                self.screen_index = 0
                                self.cycles_remaining -= 1
                                if self.cycles_remaining <= 0:
                                    self.display_state = self.IDLE
                                    self.state_start_time = time.time()

                elif self.display_state == self.IDLE:
                    # Clear or do nothing
                    self.device.clear()

            time.sleep(0.1)

    # -----------
    # Public API
    # -----------
    def show_lightning_animation(self, duration=3):
        """
        Show a lightning animation for 'duration' seconds.
        (Blocking: runs in this function.)
        """
        start_time = time.time()
        while time.time() - start_time < duration:
            # 1) Draw random lightning
            with canvas(self.device) as draw:
                draw.rectangle((0, 0, self.device.width, self.device.height), outline="black", fill="black")
                self._draw_lightning(draw)

            time.sleep(0.1)

            # 2) Quick flash off
            with canvas(self.device) as draw:
                draw.rectangle((0, 0, self.device.width, self.device.height), outline="black", fill="black")
            time.sleep(0.05)

    def set_new_order(self, order_data):
        """
        Called when a new order arrives.
        Creates screens, resets scroll, enters CELEBRATION state, etc.
        """
        self.order_data = order_data
        self.screens = self._create_order_screens(order_data)
        self.scroll_position = 0

        self.display_state = self.CELEBRATION
        self.state_start_time = time.time()

    # -----------
    # Internal Helpers
    # -----------
    def _draw_lightning(self, draw):
        """
        Draws a random lightning bolt.
        """
        width  = self.device.width
        height = self.device.height

        start_x = random.randint(width // 4, (width // 4) * 3)
        start_y = 0

        segments = []
        current_x, current_y = start_x, start_y
        num_segments = random.randint(5, 8)
        for _ in range(num_segments):
            dx = random.randint(-width // 4, width // 4)
            dy = random.randint(height // 8, height // 6)
            new_x = max(0, min(width - 1, current_x + dx))
            new_y = max(0, min(height - 1, current_y + dy))
            segments.append((current_x, current_y, new_x, new_y))
            current_x, current_y = new_x, new_y

        for (x1, y1, x2, y2) in segments:
            draw.line((x1, y1, x2, y2), fill="white", width=1)

    def _show_celebration_screen(self, draw):
        """
        Simple "New Order" text.
        """
        draw.rectangle((0, 0, self.device.width - 1, self.device.height - 1), outline="white", fill="black")
        message = "New Order!"
        msg_width = draw.textlength(message, font=self.font)
        msg_x = (self.device.width - msg_width) // 2
        msg_y = (self.device.height - 12) // 2
        draw.text((msg_x, msg_y), message, font=self.font, fill="white")

    def _create_order_screens(self, data):
        """
        Build a list of multiline screens from the order data.
        """
        total_items = sum(item['quantity'] for item in data['line_items'])
        screen_data = [
            f"Order {data['name']}",
            f"Total: {data['total_price']} {data['currency']}",
            f"Items: {total_items}",
            f"Customer:\n{data['customer']['first_name']}",
            *[f"Product:\n{item['name']}" for item in data['line_items']]
        ]

        # Group them: 2 lines per screen
        screens = []
        temp = []
        lines_per_screen = 2
        for line in screen_data:
            temp.append(line)
            if len(temp) == lines_per_screen:
                screens.append("\n".join(temp))
                temp = []
        if temp:
            screens.append("\n".join(temp))

        return screens

    def _draw_multiline_centered(self, draw, text, offset=0):
        """
        Draw multiline text, with optional horizontal scrolling if it's wider than the screen.
        """
        lines = text.split("\n")
        y_cursor = 0
        line_height = 14  # for ~12px font

        for line in lines:
            line_width = draw.textlength(line, font=self.font)
            if line_width > self.device.width:
                # Scroll horizontally
                draw.text((self.device.width - offset, y_cursor), line, font=self.font, fill="white")
            else:
                x = (self.device.width - line_width) // 2
                draw.text((x, y_cursor), line, font=self.font, fill="white")
            y_cursor += line_height


# ==========================
# 3. Order Web App (Flask)
# ==========================
class OrderWebApp:
    """
    Encapsulates the Flask server logic, including the /webhook/order route,
    and ties together the DisplayManager + LEDManager.
    """
    def __init__(self, display_manager, led_manager, port=5000):
        self.app = Flask(__name__)
        self.display_manager = display_manager
        self.led_manager = led_manager
        self.port = port

        # Set up routes
        self._init_routes()

    def _init_routes(self):
        @self.app.route('/webhook/order', methods=['POST'])
        def order_webhook():
            data = request.json
            print("Received Order:", data)

            # Blink LED
            threading.Thread(target=self.led_manager.blink, kwargs={'times':45}).start()

            # Optional Sound
            # pygame.mixer.init()
            # alert_sound = pygame.mixer.Sound("alert.wav")
            # alert_sound.play()

            # Show lightning (blocking) animation
            self.display_manager.show_lightning_animation(duration=2)

            # Then start the "celebration" and order info cycle
            self.display_manager.set_new_order(data)

            return '', 200

    def run(self):
        """
        Launch the Flask server (with ngrok) and block.
        """
        # Start ngrok tunnel
        ngrok_tunnel = ngrok.connect(self.port)
        print(f"Webhook URL: {ngrok_tunnel.public_url}/webhook/order")

        # Run Flask
        self.app.run(host='0.0.0.0', port=self.port)


# ==========================
# 4. Main Entry Point
# ==========================
if __name__ == "__main__":
    load_dotenv()  # if you need environment variables

    # Optional: pygame mixer init if using sounds
    # pygame.mixer.init()

    # Create Managers
    led_manager = LEDManager(gpio_pin=17)
    display_manager = DisplayManager(width=128, height=64, rotate=0)

    # Start display thread
    display_manager.start()

    # Create and run Flask app
    web_app = OrderWebApp(display_manager, led_manager, port=5000)
    try:
        web_app.run()
    finally:
        # Cleanup resources on exit
        display_manager.stop()
        led_manager.cleanup()
