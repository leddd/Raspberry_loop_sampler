import time
import threading
import RPi.GPIO as GPIO
from gpiozero import Button
from PIL import Image, ImageDraw, ImageFont
from luma.core.interface.serial import i2c, spi
from luma.oled.device import sh1106

class RotaryEncoder:
    def __init__(self, clk_pin, dt_pin, sw_pin, callback=None):
        self.CLK_PIN = clk_pin
        self.DT_PIN = dt_pin
        self.SW_PIN = sw_pin
        self.callback = callback

        self.DIRECTION_CW = 0
        self.DIRECTION_CCW = 1

        self.counter = 0
        self.direction = self.DIRECTION_CW
        self.prev_CLK_state = GPIO.HIGH

        self.button_pressed = False
        self.prev_button_state = GPIO.HIGH

        # Setup GPIO
        GPIO.setwarnings(False)
        GPIO.cleanup()
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.CLK_PIN, GPIO.IN)
        GPIO.setup(self.DT_PIN, GPIO.IN)
        GPIO.setup(self.SW_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # Read the initial state of the rotary encoder's CLK pin
        self.prev_CLK_state = GPIO.input(self.CLK_PIN)

    def handle_rotary_encoder(self):
        while True:
            CLK_state = GPIO.input(self.CLK_PIN)
            DT_state = GPIO.input(self.DT_PIN)

            if CLK_state != self.prev_CLK_state:
                if DT_state != CLK_state:
                    self.direction = self.DIRECTION_CW
                else:
                    self.direction = self.DIRECTION_CCW

                self.counter += 1
                if self.counter % 2 == 0:
                    if self.callback:
                        self.callback(self.direction)

            self.prev_CLK_state = CLK_state
            time.sleep(0.001)

    def handle_encoder_button(self):
        while True:
            button_state = GPIO.input(self.SW_PIN)
            if button_state != self.prev_button_state:
                time.sleep(0.01)  # Debounce
                if button_state == GPIO.LOW:
                    self.button_pressed = True
                    if self.callback:
                        self.callback("button")
                else:
                    self.button_pressed = False

            self.prev_button_state = button_state
            time.sleep(0.001)

class MenuScreen:
    def __init__(self):
        # Initialize I2C interface and OLED display
        self.serial = i2c(port=1, address=0x3C)
        self.device = sh1106(self.serial)

        # Path to your TTF font file
        self.font_path = 'fonts/InputSansNarrow-Thin.ttf'

        # CONFIG options
        self.config_options = ["BPM", "TIME SIGNATURE", "TOTAL BARS"]
        self.config_option_values = {
            "BPM": 120,
            "TIME SIGNATURE": "4/4",
            "TOTAL BARS": 4
        }
        self.time_signature_options = ["2/4", "3/4", "4/4"]
        self.current_config_option = 0
        self.lock = threading.Lock()

    def update_value(self, direction):
        with self.lock:
            option = self.config_options[self.current_config_option]
            if option == "BPM":
                if direction == RotaryEncoder.DIRECTION_CW:
                    self.config_option_values[option] += 1
                    if self.config_option_values[option] > 200:
                        self.config_option_values[option] = 200
                else:
                    self.config_option_values[option] -= 1
                    if self.config_option_values[option] < 40:
                        self.config_option_values[option] = 40
            elif option == "TIME SIGNATURE":
                index = self.time_signature_options.index(self.config_option_values[option])
                if direction == RotaryEncoder.DIRECTION_CW:
                    index = (index + 1) % len(self.time_signature_options)
                else:
                    index = (index - 1) % len(self.time_signature_options)
                self.config_option_values[option] = self.time_signature_options[index]
            elif option == "TOTAL BARS":
                if direction == RotaryEncoder.DIRECTION_CW:
                    self.config_option_values[option] += 1
                    if self.config_option_values[option] > 16:
                        self.config_option_values[option] = 16
                else:
                    self.config_option_values[option] -= 1
                    if self.config_option_values[option] < 1:
                        self.config_option_values[option] = 1

            print(f"{option}: {self.config_option_values[option]}")

    def next_option(self):
        with self.lock:
            self.current_config_option = (self.current_config_option + 1) % len(self.config_options)
            print(f"Switched to: {self.config_options[self.current_config_option]}")

    def draw_config_screen(self):
        while True:
            with self.lock:
                # Create an image in portrait mode dimensions
                image = Image.new('1', (64, 128), "black")
                draw = ImageDraw.Draw(image)
                
                # Load a custom font
                font_size = 12  # Adjust the font size as needed
                font = ImageFont.truetype(self.font_path, font_size)

                # Draw config option
                option = self.config_options[self.current_config_option]
                if option == "BPM":
                    value = f"{self.config_option_values[option]} BPM"
                elif option == "TIME SIGNATURE":
                    value = self.config_option_values[option]
                elif option == "TOTAL BARS":
                    value = f"{self.config_option_values[option]} BARS"

                # Calculate text position
                bbox = draw.textbbox((0, 0), value, font=font)  # Get bounding box
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                text_x = (64 - text_width) // 2
                text_y = (128 - text_height) // 2  # Slightly below center, moved 5 pixels up

                # Draw text on the screen
                draw.text((text_x, text_y), value, font=font, fill="white")
                
                # Rotate the image by 90 degrees to fit the landscape display
                rotated_image = image.rotate(270, expand=True)
                
                # Display the rotated image on the device
                self.device.display(rotated_image)
            
            time.sleep(0.1)  # Update the screen every 0.1 seconds

def main():
    menu_screen = MenuScreen()
    rotary_encoder = RotaryEncoder(clk_pin=CLK_PIN, dt_pin=DT_PIN, sw_pin=SW_PIN, callback=menu_screen.update_value)
    
    # Start threads for handling the rotary encoder, button press, and screen update
    threading.Thread(target=rotary_encoder.handle_rotary_encoder, daemon=True).start()
    threading.Thread(target=rotary_encoder.handle_encoder_button, daemon=True).start()
    threading.Thread(target=menu_screen.draw_config_screen, daemon=True).start()

    # Keep the main thread running
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
